import os
import re
from pathlib import Path
from anthropic import AsyncAnthropic

RESUME_TEXT = (Path(__file__).parent / "resume_context.txt").read_text()

# ---------------------------------------------------------------------------
# Known skills → years value (always high for skills on the resume)
# ---------------------------------------------------------------------------
_YEARS_MAP: dict[str, str] = {
    "years_java":           "8",
    "years_spring_boot":    "7",
    "years_spring":         "8",
    "years_react":          "6",
    "years_nodejs":         "6",
    "years_aws":            "6",
    "years_azure":          "4",
    "years_microservices":  "7",
    "years_kubernetes":     "5",
    "years_docker":         "6",
    "years_kafka":          "4",
    "years_typescript":     "5",
    "years_sql":            "8",
    "years_python":         "4",
    "years_graphql":        "4",
    "years_hibernate":      "7",
    "years_jpa":            "7",
    "years_oauth":          "5",
    "years_jwt":            "5",
    "years_ci_cd":          "6",
    "years_terraform":      "4",
    "years_git":            "8",
    "years_agile":          "7",
    "years_angular":        "4",
    "years_redux":          "5",
    "years_mongodb":        "5",
    "years_postgresql":     "5",
    "years_dynamodb":       "4",
    "years_redis":          "4",
    "years_jenkins":        "5",
    "years_linux":          "6",
    # Skills related but not primary → still credible
    "years_scala":          "2",
    "years_go":             "1",
    "years_rust":           "1",
    "years_php":            "2",
    "years_ruby":           "1",
    "years_swift":          "1",
}

# Maps question keyword fragments → config/years answer key
_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("authorized to work", "legally authorized", "work in the u.s", "work in the us"), "authorized_to_work_us"),
    (("sponsor", "visa"), "require_sponsorship"),
    (("salary", "compensation", "annual pay", "expected pay", "desired pay"), "salary_expectation_annual"),
    (("hourly rate", "hourly pay", "hourly comp", "bill rate"), "salary_expectation_hourly"),
    (("start date", "earliest start", "when can you start", "available to start"), "desired_start_date"),
    (("notice period",), "notice_period"),
    (("currently employed", "are you employed", "current employment"), "currently_employed"),
    (("relocat",), "willing_to_relocate"),
    (("remote", "on-site", "onsite", "hybrid", "work arrangement", "work location", "work model"), "work_preference"),
    (("full-time", "full time", "employment type", "contract", "w2", "c2c", "corp"), "employment_type"),
    (("security clearance", "clearance"), "security_clearance"),
    (("highest level of education", "education level", "highest degree"), "education_level"),
    (("field of study", "major", "area of study"), "field_of_study"),
    (("gpa", "grade point"), "gpa"),
    (("linkedin profile", "linkedin url"), "linkedin_url"),
    (("github", "gitlab"), "github_url"),
    (("phone", "mobile number", "cell"), "phone"),
    (("email address", "email id"), "email"),
    (("how did you hear", "referred by", "source of"), "how_did_you_hear"),
    (("gender",), "gender"),
    (("race", "ethnicity"), "ethnicity"),
    (("veteran",), "veteran_status"),
    (("disability",), "disability_status"),
    # Years of experience — ordered most-specific first
    (("java", "spring boot"), "years_spring_boot"),
    (("java", "spring"), "years_spring"),
    (("java",), "years_java"),
    (("react",), "years_react"),
    (("node",), "years_nodejs"),
    (("angular",), "years_angular"),
    (("typescript",), "years_typescript"),
    (("redux",), "years_redux"),
    (("aws", "amazon web"), "years_aws"),
    (("azure",), "years_azure"),
    (("microservice",), "years_microservices"),
    (("kubernetes", "k8s"), "years_kubernetes"),
    (("docker",), "years_docker"),
    (("kafka",), "years_kafka"),
    (("graphql",), "years_graphql"),
    (("sql",), "years_sql"),
    (("python",), "years_python"),
    (("hibernate",), "years_hibernate"),
    (("jpa",), "years_jpa"),
    (("oauth",), "years_oauth"),
    (("jwt",), "years_jwt"),
    (("ci/cd", "cicd", "jenkins", "devops pipeline"), "years_ci_cd"),
    (("terraform",), "years_terraform"),
    (("git",), "years_git"),
    (("agile", "scrum"), "years_agile"),
    (("mongodb", "mongo"), "years_mongodb"),
    (("postgresql", "postgres"), "years_postgresql"),
    (("dynamodb",), "years_dynamodb"),
    (("redis",), "years_redis"),
    (("linux",), "years_linux"),
]

# Question patterns that always expect a plain integer
_NUMERIC_LABEL_PATTERNS = re.compile(
    r"how many years|years of experience|years with|years using|"
    r"years in|number of years|experience \(years\)|experience in years",
    re.IGNORECASE,
)


def _to_number_only(value: str) -> str:
    """Strip any non-digit text from a year/number answer."""
    m = re.search(r"\d+", value)
    return m.group() if m else value


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
        # Determine if this field expects a bare number
        expects_number = (
            field_type == "number"
            or bool(_NUMERIC_LABEL_PATTERNS.search(question))
        )

        # 1. Profile fields
        profile_answer = self._profile_lookup(question)
        if profile_answer:
            ans = self._best_option(profile_answer, options) if options else profile_answer
            return _to_number_only(ans) if expects_number else ans

        # 2. Config / years lookup
        config_answer = self._config_lookup(question)
        if config_answer and config_answer != "FILL_IN":
            ans = self._best_option(config_answer, options) if options else config_answer
            return _to_number_only(ans) if expects_number else ans

        # 3. Claude fallback
        answer = await self._ask_claude(question, field_type, job_title, company, options, expects_number)
        return _to_number_only(answer) if expects_number else answer

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
            if all(kw in q for kw in keywords):
                # Check years map first, then answers block
                value = _YEARS_MAP.get(answer_key) or self.answers.get(answer_key)
                if value:
                    return value
        return None

    def _best_option(self, answer: str, options: list[str]) -> str:
        a = answer.strip().lower()
        for opt in options:
            if opt.strip().lower() == a:
                return opt
        for opt in options:
            opt_l = opt.strip().lower()
            if a in opt_l or opt_l in a:
                return opt
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
        expects_number: bool = False,
    ) -> str:
        options_block = (
            "\nAvailable options:\n" + "\n".join(f"  - {o}" for o in options)
            if options else ""
        )

        if expects_number:
            type_instruction = (
                "This field expects a NUMBER ONLY — no units, no words like 'years'. "
                "Return a single integer. "
                "For any technology that appears in the resume, return a number >= 5. "
                "For skills related but not listed, return 2 or 3. "
                "For unrelated skills, return 1."
            )
        else:
            type_instruction = {
                "text": "Respond with a concise answer (1 sentence or short phrase).",
                "number": "Return a single integer, no units.",
                "select": f"Choose EXACTLY one option from the list.{options_block}",
                "radio": f"Choose EXACTLY one option from the list.{options_block}",
                "textarea": (
                    "Write a professional 3-4 sentence response highlighting relevant "
                    "experience from the resume. Be specific and confident."
                ),
                "checkbox": "Respond with Yes or No.",
            }.get(field_type, f"Respond concisely.{options_block}")

        system_prompt = (
            f"You are filling out a job application form for:\n"
            f"Candidate: {self.profile.get('name', 'Amram Raju')}\n"
            f"Role: {job_title} at {company}\n\n"
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
