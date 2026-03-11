from .openai_client import OpenAIError, create_response, extract_output_text, is_configured


def build_prompt(payload):
    draft_type = payload.get("draft_type")
    title = payload.get("title") or ""
    audience = payload.get("audience") or ""
    goals = payload.get("goals") or ""
    constraints = payload.get("constraints") or ""
    tone = payload.get("tone") or ""
    source_material = payload.get("source_material") or ""

    instruction_lines = [
        "You are Studio, an expert instructional designer and evaluator.",
        "Produce a draft that is precise, structured, and ready for human review.",
        "Avoid generic advice. Use concrete activities, timings, and assessment criteria.",
        "Output in Portuguese (Brazil) and keep formatting readable.",
    ]

    prompt_lines = [
        "Briefing:",
        f"Tipo: {draft_type}",
        f"Titulo: {title}",
        f"Publico: {audience}",
        f"Objetivos: {goals}",
        f"Restricoes: {constraints}",
        f"Tom: {tone}",
        f"Material base: {source_material}",
    ]

    return "\n".join(instruction_lines + [""] + prompt_lines)


def generate_draft(payload):
    if not is_configured():
        return (
            "IA indisponivel. Configure OPENAI_API_KEY para gerar rascunhos.",
            None,
        )

    prompt = build_prompt(payload)
    input_messages = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": "Studio IA para autoria de cursos."}],
        },
        {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
    ]
    try:
        response = create_response(input_messages)
        output = extract_output_text(response)
        return (output or "", response)
    except OpenAIError as exc:
        return (f"Erro ao chamar IA: {exc}", None)
