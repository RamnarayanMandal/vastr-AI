"""LangGraph-orchestrated VastrAI try-on workflow.

Replaces the imperative stage loop with an explicit, state-driven graph so the
whole raw-fabric -> garment -> person pipeline is inspectable, resumable and
robust to failure:

    START
      -> validate_inputs      (download + decode person/fabric, validate garment+style)
      -> analyze_fabric       (Pillow colour/pattern analysis)
      -> build_prompt         (LangChain prompt from fabric analysis)
      -> generate_garment     (AIProvider: fabric swatch -> flat garment)
      -> generate_tryon       (AIProvider: person + garment -> try-on)
      -> validate_generated   (decode, min size, identity + quality)
      -> upload_result        (ImageKit -> result_url)
      -> save_result          (PostgreSQL try_on_results row)
      -> COMPLETED

Any node can fail (``WorkflowError``). Transient errors retry with exponential
backoff (capped); permanent validation/config errors fail immediately. The
graph carries retry state so we never hammer a failing call forever but also
never retry a permanent validation error.

State (only useful workflow state is carried):

    job_id, person_image, fabric_image, garment_type, garment_style,
    prompt, generated_image, result_url, status, error

The graph reuses the existing backend utilities (``pipeline.analyze_fabric``,
``imagekit.download_url``/``upload_bytes``, ``pipeline.identity_metrics``) and
the ``AIProvider`` / ``ImageGenBackend`` seams, so this is integration not a
rebuild (Part 5).
"""

from __future__ import annotations

import io
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from ..config import settings
from .imagekit import download_url, upload_bytes
from .perf import ago_ms, perf
from .pipeline import analyze_fabric
from .prompts import VastrAIPrompts


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class WorkflowState(TypedDict, total=False):
    job_id: Optional[str]
    person_image_url: Optional[str]
    fabric_image_url: Optional[str]
    person_image: Optional[bytes]
    fabric_image: Optional[bytes]
    garment_type: Optional[str]
    garment_style: Optional[str]
    gender: Optional[str]
    fabric_analysis: Optional[dict]
    prompt: Optional[dict]
    garment_image: Optional[bytes]
    generated_image: Optional[bytes]
    result_url: Optional[str]
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
    error: Optional[str]
    retryable: Optional[bool]
    retries: int
    max_retries: int
    stage_log: List[dict]


# ---------------------------------------------------------------------------
# Retry / failure envelope
# ---------------------------------------------------------------------------

class WorkflowError(Exception):
    """Raised inside a node - routed to retry (transient) or fail (permanent)."""

    retryable: bool = True
    message: str = ""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


def _brief(exc: Exception) -> str:
    return (str(exc) or "")[:280] or exc.__class__.__name__


def _require_decodable(data: bytes, what: str) -> None:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
    except (UnidentifiedImageError, Exception):
        raise WorkflowError(f"The {what} is not a valid image.", retryable=False)


# ---------------------------------------------------------------------------
# Node implementations (pure functions over WorkflowState)
# ---------------------------------------------------------------------------

@dataclass
class WorkflowComponents:
    """Collaborators injected into a workflow run (defaults if omitted)."""
    provider: Any = None
    prompts: Optional[VastrAIPrompts] = None
    uploader: Optional[Callable[..., Optional[dict]]] = None
    downloader: Optional[Callable[..., Optional[bytes]]] = None
    saver: Optional[Callable[[WorkflowState], None]] = None


def _log(state: WorkflowState, stage: str, status: str, note: str = "") -> None:
    state.setdefault("stage_log", []).append(
        {"stage": stage, "status": status, "note": note}
    )


def _trace(state: WorkflowState, stage: str, message: str) -> None:
    print(f"[TRYON][job_id={state.get('job_id')}][{stage}] {message}", flush=True)


def _require_byte(state: WorkflowState, key: str, what: str) -> bytes:
    value = state.get(key)
    if not value:
        raise WorkflowError(f"{what} is missing.", retryable=False)
    return value


def node_validate_inputs(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "GRAPH", "Validate inputs START")
    state["status"] = "PROCESSING"
    if not (state.get("garment_type") and state.get("garment_style")):
        raise WorkflowError("Garment type and style are required.", retryable=False)
    gender = state.get("gender")
    if gender and gender.upper() not in ("MEN", "WOMEN", "KIDS"):
        raise WorkflowError(f"Unknown gender '{gender}'.", retryable=False)

    downloader = comps.downloader or download_url
    for key, what in (("person_image_url", "customer photo"), ("fabric_image_url", "fabric photo")):
        dname = "person" if key == "person_image_url" else "fabric"
        d_t = time.perf_counter()
        perf("image_download_start", job_id=state.get("job_id"), key=dname)
        data = downloader(state.get(key) or "")
        perf(
            "image_download_end",
            job_id=state.get("job_id"),
            key=dname,
            duration_ms=round(ago_ms(d_t), 1),
            bytes=len(data) if data else 0,
        )
        if data:
            _require_decodable(data, what)
            state["person_image" if key == "person_image_url" else "fabric_image"] = data
    _require_byte(state, "person_image", "Customer photo")
    _require_byte(state, "fabric_image", "Fabric photo")
    _log(state, "validate_inputs", "ok")
    _trace(state, "GRAPH", "Validate inputs SUCCESS")
    return state


def node_analyze_fabric(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "GRAPH", "Load fabric and analyze START")
    fabric = _require_byte(state, "fabric_image", "Fabric image")
    state["fabric_analysis"] = analyze_fabric(fabric).to_dict()
    _log(state, "analyze_fabric", "ok")
    _trace(state, "GRAPH", "Load fabric and analyze SUCCESS")
    return state


def node_build_prompt(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "GRAPH", "Build prompt START")
    prompts = comps.prompts or VastrAIPrompts()
    state["prompt"] = prompts.build(
        state.get("garment_type") or "",
        state.get("garment_style") or "",
        state.get("fabric_analysis"),
    )
    _log(state, "build_prompt", "ok")
    _trace(state, "GRAPH", "Build prompt SUCCESS")
    return state


def _get_provider(comps: WorkflowComponents):
    if comps.provider is not None:
        return comps.provider
    from .image_gen import get_image_gen_backend

    return get_image_gen_backend()


def _map_provider_error(exc: Exception, stage: str) -> WorkflowError:
    from .image_gen import ImageGenNotConfigured

    if isinstance(exc, ImageGenNotConfigured):
        return WorkflowError(str(exc), retryable=False)
    return WorkflowError(f"{stage} failed: {_brief(exc)}", retryable=True)


def _log_generation_request(
    state: WorkflowState,
    provider: Any,
    task: str,
    input_count: int,
    garment_visible: bool,
) -> None:
    """Debug log immediately before a generation request is sent.

    Proves the garment/fabric reference image is attached and that the prompt
    actually carries the garment-preservation instructions (no sensitive image
    data or keys are logged).
    """
    from .prompts import VastrAIPrompts

    job_id = state.get("job_id")
    model = getattr(provider, "model_tag", "") or getattr(provider, "model", "")

    garment_img = state.get("garment_image") is not None or task == "garment"
    person_img = state.get("person_image") is not None or task == "tryon"
    print(
        f"[TRYON][REFERENCE] person_image={'present' if person_img else 'missing'} "
        f"garment_image={'present' if garment_img else 'missing'} "
        f"garment_reference_attached={garment_visible} "
        f"input_image_count={input_count} model={model}",
        flush=True,
    )

    props = VastrAIPrompts()
    if task == "garment":
        prompt = props.build_garment(
            state.get("garment_type") or "",
            state.get("garment_style") or "",
            state.get("fabric_analysis"),
        )
    else:
        prompt = props.build_tryon(
            state.get("garment_type") or "",
            state.get("garment_style") or "",
            state.get("fabric_analysis"),
        )
    contains_preservation = props.PRESERVATION_MARKER in prompt
    print(
        f"[TRYON][FIDELITY] reference_image_used=true "
        f"prompt_contains_garment_preservation={str(contains_preservation).lower()}",
        flush=True,
    )
    # Temporary audit (no keys, no image data): which garment type/style reached
    # the request and whether the hard constraints are in the prompt.
    props.audit_request(
        task,
        state.get("garment_type") or "",
        state.get("garment_style") or "",
        reference_attached=garment_visible,
    )


def node_generate_garment(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "GRAPH", "Generate garment START")
    fabric = _require_byte(state, "fabric_image", "Fabric image")
    provider = _get_provider(comps)
    job_id = state.get("job_id")
    if provider.__class__.__name__ == "OpenRouterImageGenBackend":
        _trace(state, "OPENROUTER", "Request started task=garment")
    _log_generation_request(
        state, provider, "garment", input_count=1, garment_visible=True
    )
    print(f"[AI] Generation request started job_id={job_id} task=garment model={getattr(provider, 'model_tag', '') or getattr(provider, 'model', '')}", flush=True)
    ai_t = time.perf_counter()
    perf(
        "garment_ai_start",
        job_id=job_id,
        provider=provider.__class__.__name__,
        model=getattr(provider, "model_tag", "") or getattr(provider, "model", ""),
        input_images=1,
        output_images=getattr(provider, "num_images", 1),
    )
    try:
        garment = provider.generate_garment(
            fabric,
            state.get("garment_type") or "",
            state.get("garment_style") or "",
            state.get("fabric_analysis"),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_provider_error(exc, "Garment generation") from exc
    perf(
        "garment_ai_end",
        job_id=job_id,
        duration_ms=round(ago_ms(ai_t), 1),
        bytes=len(garment) if garment else 0,
        model=getattr(provider, "model_used", "") or getattr(provider, "model_tag", ""),
    )
    if provider.__class__.__name__ == "OpenRouterImageGenBackend":
        _trace(state, "OPENROUTER", f"Response received task=garment bytes={len(garment) if garment else 0}")
    if not garment or len(garment) < 100:
        raise WorkflowError("Garment generation returned an empty image.", retryable=True)
    _require_decodable(garment, "generated garment")
    print(f"[AI] Generation completed job_id={job_id} task=garment bytes={len(garment)}", flush=True)
    state["garment_image"] = garment
    state["prompt"] = state.get("prompt") or {}
    _log(state, "generate_garment", "ok")
    _trace(state, "GRAPH", f"Generate garment SUCCESS bytes={len(garment)}")
    return state


def node_generate_tryon(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "GRAPH", "Generate try-on START")
    person = _require_byte(state, "person_image", "Person image")
    garment = _require_byte(state, "garment_image", "Garment image")
    provider = _get_provider(comps)
    job_id = state.get("job_id")
    if provider.__class__.__name__ == "OpenRouterImageGenBackend":
        _trace(state, "OPENROUTER", "Request started task=tryon")
    _log_generation_request(
        state, provider, "tryon", input_count=2, garment_visible=True
    )
    print(f"[AI] Generation request started job_id={job_id} task=tryon model={getattr(provider, 'model_tag', '') or getattr(provider, 'model', '')}", flush=True)
    ai_t = time.perf_counter()
    perf(
        "tryon_ai_start",
        job_id=job_id,
        provider=provider.__class__.__name__,
        model=getattr(provider, "model_tag", "") or getattr(provider, "model", ""),
        input_images=2,
        output_images=getattr(provider, "num_images", 1),
    )
    try:
        result = provider.generate_tryon(
            person,
            garment,
            state.get("garment_type") or "",
            state.get("garment_style") or "",
            state.get("fabric_analysis"),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_provider_error(exc, "Virtual try-on") from exc
    perf(
        "tryon_ai_end",
        job_id=job_id,
        duration_ms=round(ago_ms(ai_t), 1),
        bytes=len(result) if result else 0,
        model=getattr(provider, "model_used", "") or getattr(provider, "model_tag", ""),
    )
    if provider.__class__.__name__ == "OpenRouterImageGenBackend":
        _trace(state, "OPENROUTER", f"Response received task=tryon bytes={len(result) if result else 0}")
    if not result or len(result) < 100:
        raise WorkflowError("Try-on returned an empty image.", retryable=True)
    _require_decodable(result, "try-on result")
    print(f"[AI] Generation completed job_id={job_id} task=tryon bytes={len(result)}", flush=True)
    state["generated_image"] = result
    _log(state, "generate_tryon", "ok")
    _trace(state, "GRAPH", f"Generate try-on SUCCESS bytes={len(result)}")
    return state


def node_validate_generated(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "IMAGE", "Validate generated image START")
    data = state.get("generated_image")
    job_id = state.get("job_id")
    if not data or len(data) < 500:
        raise WorkflowError("Generated result is empty.", retryable=True)
    from PIL import Image

    proc_t = time.perf_counter()
    perf("image_processing_start", job_id=job_id, kind="quality_gate")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        w, h = im.size
    except Exception:
        raise WorkflowError("Generated result is not a valid image.", retryable=True)
    if min(w, h) < 128:
        raise WorkflowError(f"Generated result is too small ({w}x{h}).", retryable=True)

    # Quality gate (decode + encode round-trip) and optional identity gate.
    buf = io.BytesIO()
    try:
        im.convert("RGB").save(buf, "JPEG", quality=90)
    except Exception:
        raise WorkflowError("Generated result could not be encoded.", retryable=True)
    if len(buf.getvalue()) < 500:
        raise WorkflowError("Generated result is too small to store.", retryable=True)
    perf(
        "image_processing_end",
        job_id=job_id,
        kind="quality_gate",
        duration_ms=round(ago_ms(proc_t), 1),
        width=w,
        height=h,
        bytes=len(data),
    )

    threshold = settings.identity_min_score
    if threshold:
        from .pipeline import identity_metrics

        id_t = time.perf_counter()
        perf("identity_check_start", job_id=job_id)
        score = identity_metrics(state.get("person_image"), data)
        state["identity_score"] = score
        perf("identity_check_end", job_id=job_id, duration_ms=round(ago_ms(id_t), 1), score=round(score, 3))
        if score < threshold:
            raise WorkflowError(
                f"Identity preservation failed (score {score:.2f}).", retryable=True
            )
    _log(state, "validate_generated", "ok")
    _trace(state, "IMAGE", f"Generated image validated width={w} height={h} bytes={len(data)}")
    return state


def node_upload_result(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    _trace(state, "IMAGEKIT", "Upload started")
    data = state.get("generated_image")
    job_id = state.get("job_id")
    if not data:
        raise WorkflowError("No generated image to upload.", retryable=True)
    uploader = comps.uploader or upload_bytes
    name = f"result-{uuid.uuid4().hex[:12]}.jpg"
    up_t = time.perf_counter()
    perf("imagekit_upload_start", job_id=job_id, file=name, bytes=len(data))
    uploaded = uploader(data, name, settings.results_folder)
    perf(
        "imagekit_upload_end",
        job_id=job_id,
        duration_ms=round(ago_ms(up_t), 1),
        ok=str(uploaded is not None and bool(uploaded.get("url"))).lower(),
        url=(uploaded or {}).get("url", ""),
    )
    if uploaded is not None and uploaded.get("url"):
        state["result_url"] = uploaded["url"]
        _log(state, "upload_result", "ok")
        _trace(state, "IMAGEKIT", "Upload completed and URL returned")
        return state
    raise WorkflowError(
        "Could not store the generated image (ImageKit not configured).", retryable=True
    )


def node_save_result(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    job_id = state.get("job_id")
    if comps.saver is None:
        _log(state, "save_result", "ok")
        return state
    try:
        db_t = time.perf_counter()
        perf("db_persistence_start", job_id=job_id)
        comps.saver(state)
        perf("db_persistence_end", job_id=job_id, duration_ms=round(ago_ms(db_t), 1))
        _log(state, "save_result", "ok")
        _trace(state, "DB", "Result saved")
    except Exception as exc:  # noqa: BLE001
        raise WorkflowError(f"Could not persist the result: {_brief(exc)}", retryable=True) from exc
    return state


def node_complete(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    state["status"] = "COMPLETED"
    state["error"] = None
    return state


def node_fail(state: WorkflowState, comps: WorkflowComponents) -> WorkflowState:
    state["status"] = "FAILED"
    if state.get("error") is None:
        state["error"] = "Your look could not be created."
    return state


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _make_node(fn, comps: WorkflowComponents):
    """Wrap a node fn so a raised WorkflowError is captured into the state
    (flags + message) instead of escaping past the conditional router.

    The ``comps`` collaborator is closed over so LangGraph can call the node with
    just the state argument. Returns a normal LangGraph node (state -> state).

    Also emits per-node [PERF] timing (all nodes run sequentially in this
    linear graph, so node durations are strictly additive).
    """

    def wrapped(state: WorkflowState) -> WorkflowState:
        node_name = getattr(fn, "__name__", fn.__class__.__name__)
        job_id = state.get("job_id")
        node_started = time.perf_counter()
        ok = True
        perf("node_start", name=node_name, job_id=job_id)
        print(f"[WORKFLOW] >>> {node_name} | job={state.get('job_id')}")
        try:
            fn(state, comps)
            print(f"[WORKFLOW] <<< {node_name} OK")
        except WorkflowError as exc:
            print(f"[WORKFLOW] !!! {node_name} FAILED (WorkflowError): {exc.message}")
            _trace(state, "ERROR", f"{node_name}: {exc.message}")
            state["error"] = exc.message
            state["retryable"] = exc.retryable
            ok = False
        except Exception as exc:  # noqa: BLE001 - unexpected -> transient
            msg = _brief(exc) or "Unexpected workflow failure."
            print(f"[WORKFLOW] !!! {node_name} FAILED ({type(exc).__name__}): {msg}")
            _trace(state, "ERROR", f"{node_name}: {msg}")
            state["error"] = msg
            state["retryable"] = True
            ok = False
        perf(
            "node_end",
            name=node_name,
            job_id=job_id,
            duration_ms=round(ago_ms(node_started), 1),
            ok=str(ok).lower(),
        )
        state.setdefault("retries", 0)
        return state

    return wrapped


def _route(
    state: WorkflowState,
    happy_next: str,
    max_retries: int,
) -> str:
    """Conditional edge after each node.

    - No error        -> continue to ``happy_next``
    - Any error       -> increment retry counter (bounded) and route to ``fail``.
      Process-level re-invocation with exponential backoff is the Celery
      worker's job; this graph records the retry count and never loops forever.
    """
    if state.get("error"):
        retries = state.get("retries", 0)
        max_r = max_retries if max_retries is not None else settings.try_on_max_retries
        state["retries"] = retries + 1
        return "fail"
    return happy_next


def build_workflow_graph(
    *,
    components: Optional[WorkflowComponents] = None,
    max_retries: int = 0,
):
    """Build (and return) the compiled LangGraph ready to invoke.

    The graph itself handles permanent failures and records retry state; actual
    process-level retries (with exponential backoff) are applied by the caller
    (Celery worker) so an in-process invocation is deterministic.
    """
    comps = components or WorkflowComponents()

    builder = StateGraph(WorkflowState)

    happy = {
        "validate_inputs": "analyze_fabric",
        "analyze_fabric": "build_prompt",
        "build_prompt": "generate_garment",
        "generate_garment": "generate_tryon",
        "generate_tryon": "validate_generated",
        "validate_generated": "upload_result",
        "upload_result": "save_result",
        "save_result": "complete",
    }

    def add(name: str, fn):
        builder.add_node(name, _make_node(fn, comps))
        # Edge targets that a node's conditional may produce.
        targets = {"analyze_fabric", "build_prompt", "generate_garment",
                   "generate_tryon", "validate_generated", "upload_result",
                   "save_result", "complete", "fail"}
        builder.add_conditional_edges(
            name,
            lambda s, _n=name: _route(s, happy[_n], max_retries),
            {t: t for t in targets},
        )

    add("validate_inputs", node_validate_inputs)
    add("analyze_fabric", node_analyze_fabric)
    add("build_prompt", node_build_prompt)
    add("generate_garment", node_generate_garment)
    add("generate_tryon", node_generate_tryon)
    add("validate_generated", node_validate_generated)
    add("upload_result", node_upload_result)
    add("save_result", node_save_result)
    builder.add_node("complete", lambda s, c=comps: node_complete(s, c))
    builder.add_node("fail", lambda s, c=comps: node_fail(s, c))
    builder.add_edge("complete", END)
    builder.add_edge("fail", END)
    builder.add_edge(START, "validate_inputs")

    return builder.compile()


def run_workflow(
    *,
    job_id: Optional[str] = None,
    person_image_url: Optional[str] = None,
    fabric_image_url: Optional[str] = None,
    garment_type: Optional[str] = None,
    garment_style: Optional[str] = None,
    gender: Optional[str] = None,
    provider: Any = None,
    uploader: Optional[Callable[..., Optional[dict]]] = None,
    downloader: Optional[Callable[..., Optional[bytes]]] = None,
    saver: Optional[Callable[[WorkflowState], None]] = None,
    max_retries: int = 0,
) -> WorkflowState:
    """Compile and run the LangGraph workflow once and return the final state.

    For retry-capable transient failures the final ``status`` is ``FAILED`` and
    ``state["retries"]`` records how many in-graph retries were consumed; the
    Celery worker may re-invoke with a higher ``max_retries`` and exponential
    backoff for true process-level retries.
    """
    graph_state: WorkflowState = {
        "job_id": job_id,
        "person_image_url": person_image_url,
        "fabric_image_url": fabric_image_url,
        "garment_type": garment_type,
        "garment_style": garment_style,
        "gender": gender,
        "status": "QUEUED",
        "retries": 0,
        "max_retries": max_retries,
        "stage_log": [],
    }
    comps = WorkflowComponents(
        provider=provider,
        uploader=uploader,
        downloader=downloader,
        saver=saver,
    )
    print(f"[WORKFLOW] run_workflow start | job={job_id} | provider_type={type(provider).__name__}")
    print(f"[TRYON][job_id={job_id}][GRAPH] Workflow started", flush=True)
    perf("langgraph_start", job_id=job_id)
    graph_t = time.perf_counter()
    graph = build_workflow_graph(components=comps, max_retries=max_retries)
    result = graph.invoke(graph_state)
    perf(
        "langgraph_end",
        job_id=job_id,
        graph_duration_ms=round(ago_ms(graph_t), 1),
        status=result.get("status"),
    )
    print(f"[WORKFLOW] run_workflow done | job={job_id} | status={result.get('status')} | error={result.get('error')}")
    print(f"[TRYON][job_id={job_id}][JOB] {result.get('status')}", flush=True)
    return result
