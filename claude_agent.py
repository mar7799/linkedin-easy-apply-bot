import os
import re
from pathlib import Path
from anthropic import AsyncAnthropic

RESUME_TEXT = (Path(__file__).parent / "resume_context.txt").read_text()

# Maps lower-case keyword fragments → config answer key
_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("authorized to work", "legally authorized", "work in the u.s", "work in the us"), "authorized_to_work_us"),
    (("sponsor", "visa"), "require_sponsorship"),
    (("salary", "compensation", "annual pay", "expected pay"), "salary_expectation_annual"),
    (("hourly rate", "hourly pay", "hourly comp"), "salary_expectation_hourly"),
    (("start date", "earliest start", "when can you start"), "desired_start_date"),
    (("notice period", "two week", "2 week"), "notice_period"),
    (("currently employed", "are you employed", "current employment"), "currently_employed"),
    (("relocat",), "willing_to_relocate"),
    (("remote", "on-site", "onsite", "hybrid", "work arrangement", "work location"), "work_preference"),
    (("full-time", "full time", "employment type", "contract", "w2", "c2c"), "employment_type"),
    (("security clearance", "clearance"), "security_clearance"),
    (("highest level of education", "education level", "degree"), "education_level"),
    (("field of study", "major"), "field_of_study"),
    (("gpa",), "gpa"),
    (("linkedin profile", "linkedin url"), "linkedin_url"),
    (("github", "gitlab"), "github_url"),
    (("phone", "mobile number"), "phone"),
    (("email address",), "email"),
    (("how did you hear", "referred by", "source"), "how_did_you_hear"),
    (("gender",), "gender"),
    (("race", "ethnicity"), "ethnicity"),
    (("veteran",), "veteran_status"),
    (("disability",), "disability_status"),
    # Years of experience keys
    (("year", "java"), "years_java"),
    (("year", "spring boot"), "years_spring_boot"),
    (("year", "spring framework", "year", "spring"), "years_spring"),
    (("year", "react",), "years_react"),
    (("year", "node",), "years_nodejs"),
    (("year", "aws",), "years_aws"),
    (("year", "azure",), "years_azure"),
    (("year", "microservice",), "years_microservices"),
    (("year", "kubernetes", "year", "k8s"), "years_kubernetes"),
    (("year", "docker",), "years_docker"),
    (("year", "kafka",), "years_kafka"),
    (("year", "typescript",), "years_typescript"),
    (("year", "sql",), "years_sql"),
    (("year", "python",), "years_python"),
    (("year", "graphql",), "years_graphql"),
]


class ClaudeAgent:
    def __init__(self, config: dict):
        self.config = config
        self.answers: dict[str, str] = config.get("answers", {})
        self.profile: dict[str, str] = config.get("profile", {})
        self.client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def get_answer(
        self,
        question: str,
        field_type: str,
        job_title: str,
        company: str,
        options: list[str] | None = None,
    ) -> str:
        # 1. Profile fields (name, phone, email)
        profile_answer = self._profile_lookup(question)
        if profile_answer:
            return self._best_option(profile_answer, options) if options else profile_answer

        # 2. Pre-configured Q&A
        config_answer = self._config_lookup(question)
        if config_answer and config_answer != "FILL_IN":
            return self._best_option(config_answer, options) if options else config_answer

        # 3. Claude fallback
        return await self._ask_claude(question, field_type, job_title, company, options)

    # ------------------------------------------------------------------ #
    #  Lookup helpers                                                      #
    # ------------------------------------------------------------------ #

    def _profile_lookup(self, question: str) -> str | None:
        q = question.lower()
        if "phone" in q or "mobile" in q:
            return self.profile.get("phone")
        if "email" in q:
            return self.profile.get("email")
        if "full name" in q or "your name" in q:
            return self.profile.get("name")
        if "first name" in q:
            name = self.profile.get("name", "")
            return name.split()[0] if name else None
        if "last name" in q or "surname" in q:
            name = self.profile.get("name", "")
            return name.split()[-1] if name else None
        return None

    def _config_lookup(self, question: str) -> str | None:
        q = question.lower()
        for keywords, answer_key in _KEYWORD_MAP:
            # For single-keyword tuples check any; for multi-keyword tuples require all
            if len(keywords) == 1:
                if keywords[0] in q:
                    return self.answers.get(answer_key)
            else:
                if all(kw in q for kw in keywords):
                    return self.answers.get(answer_key)
        return None

    def _best_option(self, answer: str, options: list[str]) -> str:
        """Pick the closest matching option label."""
        a = answer.strip().lower()
        for opt in options:
            if opt.strip().lower() == a:
                return opt
        for opt in options:
            opt_l = opt.strip().lower()
            if a in opt_l or opt_l in a:
                return opt
        # Skip placeholder / empty first option
        for opt in options:
            stripped = opt.strip()
            if stripped and stripped.lower() not in ("select an option", "please select", "-- select --", ""):
                return stripped
        return options[0] if options else answer

    # ------------------------------------------------------------------ #
    #  Claude                                                              #
    # ------------------------------------------------------------------ #

    async def _ask_claude(
        self,
        question: str,
        field_type: str,
        job_title: str,
        company: str,
        options: list[str] | None,
    ) -> str:
        options_block = (
            f"\nAvailable options to choose from:\n" + "\n".join(f"  - {o}" for o in options)
            if options
            else ""
        )

        type_instruction = {
            "text": "Respond with a concise answer (1 sentence or a short phrase).",
            "number": "Respond with only a number, no units or text.",
            "select": f"Choose EXACTLY one option from the list.{options_block}",
            "radio": f"Choose EXACTLY one option from the list.{options_block}",
            "textarea": (
                "Write a professional 3-4 sentence response that highlights relevant experience "
                "from the resume. Be specific and confident."
            ),
            "checkbox": "Respond with Yes or No.",
        }.get(field_type, f"Respond concisely.{options_block}")

        system_prompt = (
            f"You are filling out a LinkedIn Easy Apply form on behalf of the candidate below.\n\n"
            f"Candidate: {self.profile.get('name', 'Amram Raju')}\n"
            f"Applying for: {job_title} at {company}\n\n"
            f"Resume:\n{RESUME_TEXT}\n\n"
            f"{type_instruction}\n\n"
            f"Return ONLY the answer — no preamble, no explanation, no quotes."
        )

        response = await self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Form question: {question}"}],
        )

        return response.content[0].text.strip()
