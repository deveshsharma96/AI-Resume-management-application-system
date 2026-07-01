# parser_settings.py

# Default parser → AI
CURRENT_PARSER = "ai"   # options: "ai" | "resume"


def get_parser_type():
    return CURRENT_PARSER


def set_parser_type(parser_type: str):
    global CURRENT_PARSER

    if parser_type in ["ai", "resume"]:
        CURRENT_PARSER = parser_type