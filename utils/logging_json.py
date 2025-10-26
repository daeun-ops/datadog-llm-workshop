import json
def current_ids():
    # ddtrace 우선 (decimal)
    try:
        from ddtrace import tracer
        s = tracer.current_span()
        if s and s.trace_id:
            dec = s.trace_id
            return dec, f"{dec:016x}".rjust(32,"0")
    except Exception:
        pass
    # OTel fallback (hex)
    try:
        from opentelemetry import trace
        sc = trace.get_current_span().get_span_context()
        if sc and sc.trace_id:
            return None, f"{sc.trace_id:032x}"
    except Exception:
        pass
    return None, None

def jlog(**kw):
    dec, hexx = current_ids()
    if hexx: kw.setdefault("trace_id", hexx)
    if dec:  kw.setdefault("dd_trace_id", str(dec))
    print(json.dumps(kw, ensure_ascii=False), flush=True)
