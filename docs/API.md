# revolver — public API reference

Public function and class signatures with type hints, grouped by module.
Only the public surface is listed (no underscore-prefixed internals). Every
I/O boundary is an overridable seam (a `Callable` parameter) so the logic stays
pure and testable.

> Signatures are copied from the source. `| None` defaults and keyword-only
> arguments are shown as in the code.

## `revolver.diagnosis`

```python
class Diagnosis:
    pipeline_id: str
    failure_mode: str
    evidence: str
    endpoint_pin: str
    driver_alive: bool
    driver_death_cycle: int | None
    wall_kill_cycle: int | None
    stall_action: str
    stall_reason: str
    live_work: bool
    live_work_root: int | None
    cycles_started: list[int]
    cycles_done: list[int]
    cycles_in_flight: list[int]
    cycles_wall_kill: list[int]
    gate_blocks: list[int]
    verdict: str
    source: str
    raw: str
    sentry_exit_code: int | None
    client_timeout_cycle: int | None
    inner_wall_kill_cycle: int | None
    heaviest_inner_duration: int | None
    outer_wall: int | None
    inner_seconds: int | None
    no_new_trajectory_witnessed: bool
    pass_start_max_seq: int | None

    @property
    def action_needed(self) -> bool: ...
    @property
    def exit_code(self) -> int: ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Diagnosis: ...
    def validate(self) -> Diagnosis: ...

def parse_sentry_report(text: str) -> Diagnosis: ...
def parse_raw_artifacts(
    cycles_out_text: str = "",
    gate_log_text: str = "",
    trajectory_outcome: str = "",
) -> Diagnosis: ...
def diagnose(
    project_dir: str | Path,
    *,
    read_file: Callable[[Path], str] | None = None,
    sentry_available: bool | None = None,
    client: SentryClient | None = None,
) -> Diagnosis: ...
```

## `revolver.sentry_client`

```python
EXIT_OK: int = 0
EXIT_ACTION: int = 1
EXIT_USAGE: int = 2

class SentryClient:
    def run_check(self, project_dir: str | Path) -> tuple[str, int]: ...

def diagnose_via_sentry(
    project_dir: str | Path,
    *,
    client: SentryClient | None = None,
    read_file: Callable[[Path], str] | None = None,
) -> Diagnosis: ...
```

## `revolver.sentry_pin`

```python
DEFAULT_SENTRY_NAME: str
DEFAULT_SENTRY_URL: str
DEFAULT_SENTRY_SHA: str

@dataclass(frozen=True)
class SentryPin:
    name: str
    url: str
    sha: str

DEFAULT_SENTRY_PIN: SentryPin

def parse_requirement(req: str) -> SentryPin: ...
def render_requirement(pin: SentryPin) -> str: ...
def validate_pin(pin: SentryPin) -> bool: ...
```

## `revolver.proposal`

```python
PROPOSAL_VERSION: str = "1.0"
PROPOSAL_NAMESPACE: str = "revolver/fixes/"

@dataclass
class NewFile:
    path: str
    content: str
    diff_from_predecessor: str
    evidence: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewFile: ...

@dataclass
class RepairProposal:
    pipeline_id: str
    diagnosis: Diagnosis
    new_files: list[NewFile]
    rationale: str
    version: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairProposal: ...
    def validate(self, existing_paths: set[str] | None = None) -> RepairProposal: ...

def propose(
    diagnosis: Diagnosis,
    *,
    builders: dict[str, Callable[[Diagnosis], list[NewFile]]] | None = None,
) -> RepairProposal: ...
```

## `revolver.fixes`

```python
FIX_BUILDERS: dict[str, Callable[[Diagnosis], list[NewFile]]]

def build_driver_death_fix(diagnosis: Diagnosis) -> list[NewFile]: ...
def build_wall_kill_fix(diagnosis: Diagnosis) -> list[NewFile]: ...
def build_stall_kill_fix(diagnosis: Diagnosis) -> list[NewFile]: ...
def build_none_fix(diagnosis: Diagnosis) -> list[NewFile]: ...
def build_client_timeout_fix(diagnosis: Diagnosis, *, triple_dir: str | Path | None = None) -> list[NewFile]: ...
def build_inner_wall_fix(diagnosis: Diagnosis, *, predecessor_driver: str | None = None) -> list[NewFile]: ...
def build_outer_freshness_fix(diagnosis: Diagnosis, *, predecessor_runner: str) -> list[NewFile]: ...
```

Note: only `build_outer_freshness_fix` is **not** in `FIX_BUILDERS` (it takes a
keyword-only `predecessor_runner` and is called directly with the predecessor
text). `build_inner_wall_fix` **is** registered (`"inner-wall"`) and is
reachable via `propose()`.

## `revolver.launch_plan`

```python
LAUNCH_PLAN_VERSION: str = "1.0"

@dataclass
class LaunchPlan:
    pipeline_id: str
    command: str
    cycles_out_append: str
    endpoint_pin: str
    request_timeout: int
    outer_wall: int
    one_pipeline_per_endpoint: bool
    rationale: str
    version: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LaunchPlan: ...
    def validate(self) -> LaunchPlan: ...

def build_launch_plan(proposal: RepairProposal) -> LaunchPlan: ...
```

## `revolver.manifest`

```python
MANIFEST_VERSION: str = "1.0"

@dataclass
class ProposalManifest:
    pipeline_id: str
    diagnosis: Diagnosis
    proposal: RepairProposal
    launch_plan: LaunchPlan
    version: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProposalManifest: ...
    def validate(self, existing_paths: set[str] | None = None) -> ProposalManifest: ...
    def render(self) -> str: ...

def build_manifest(
    diagnosis: Diagnosis,
    *,
    builders: dict[str, Callable[[Diagnosis], list[NewFile]]] | None = None,
) -> ProposalManifest: ...
```

## `revolver.validation`

```python
@dataclass
class SyntaxReport:
    path: str
    ok: bool
    error: str

@dataclass
class ImportReport:
    path: str
    ok: bool
    missing: list[str]

@dataclass
class ValidationResult:
    path: str
    syntax_ok: bool
    imports_ok: bool
    errors: list[str]

@dataclass
class LaunchPlanReport:
    ok: bool
    errors: list[str]

def check_syntax(content: str, *, path: str) -> SyntaxReport: ...
def check_imports(
    content: str,
    *,
    path: str = "",
    known_modules: set[str] | None = None,
) -> ImportReport: ...
def validate_manifest_artifacts(
    manifest: ProposalManifest,
    *,
    known_modules: set[str] | None = None,
) -> list[ValidationResult]: ...
def check_launch_plan(
    plan: LaunchPlan,
    *,
    endpoint_pin: str | None = None,
) -> LaunchPlanReport: ...
def validate_manifest_launch(
    manifest: ProposalManifest,
    *,
    endpoint_pin: str | None = None,
) -> LaunchPlanReport: ...
```

## `revolver.deploy`

```python
@dataclass
class DeployReport:
    ok: bool
    deployed_paths: list[str]
    errors: list[str]
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeployReport: ...

@dataclass
class LaunchReport:
    ok: bool
    command: str
    errors: list[str]
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LaunchReport: ...

def deploy_manifest(
    manifest: ProposalManifest,
    *,
    base_dir: str | Path,
    write_file: Callable[[Path, str], None] | None = None,
    approved: Callable[[], bool] | None = None,
) -> DeployReport: ...
def relaunch(
    manifest: ProposalManifest,
    *,
    launch: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
    run_command: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
) -> LaunchReport: ...
```

## `revolver.relaunch`

```python
def first_not_done_cycle(
    cycles: Collection[int],
    *,
    done: Collection[int] | None = None,
) -> int | None: ...

@dataclass
class RelaunchPlan:
    first_cycle: int
    last_cycle: int
    resume_from: int | None
    command: str
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelaunchPlan: ...

def plan_relaunch(
    manifest: ProposalManifest,
    *,
    cycles: Collection[int],
    done: Collection[int] | None = None,
) -> RelaunchPlan: ...

@dataclass
class RelaunchVerification:
    ok: bool
    marker_appended: bool
    driver_alive: bool
    errors: list[str]
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelaunchVerification: ...

def verify_relaunch(
    manifest: ProposalManifest,
    *,
    read_cycles_out: Callable[[], str] | None = None,
    driver_alive: Callable[[], bool] | None = None,
) -> RelaunchVerification: ...
```

## `revolver.observe`

```python
@dataclass
class CycleMarker:
    cycle: int
    status: str
    raw: str

@dataclass
class Observation:
    cycles_seen: list[int]
    cycles_done: list[int]
    cycles_in_flight: list[int]
    gaps: list[int]
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Observation: ...

@dataclass
class TrajectoryOutcome:
    cycle: int
    outcome: str
    raw: str

@dataclass
class RecurrenceReport:
    failure_mode: str
    recurred: bool
    cycles_done: list[int]
    cycles_in_flight: list[int]
    gaps: list[int]
    outcomes: list[TrajectoryOutcome]
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecurrenceReport: ...

@dataclass
class MergeCommit:
    cycle: int
    sha: str
    raw: str

@dataclass
class GitObservation:
    cycles_merged: list[int]
    cycles_missing: list[int]
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GitObservation: ...

@dataclass
class FinalReport:
    failure_mode: str
    recurred: bool
    observation: Observation
    outcomes: list[TrajectoryOutcome]
    git: GitObservation
    note: str
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinalReport: ...

def parse_cycle_markers(
    text: str,
    *,
    done_pattern: re.Pattern[str] | None = None,
) -> list[CycleMarker]: ...
def observe(
    cycles: Sequence[int],
    *,
    markers: Sequence[CycleMarker] | None = None,
    read_cycles_out: Callable[[], str] | None = None,
) -> Observation: ...
def parse_trajectory_outcomes(
    text: str,
    *,
    read_trajectory: Callable[[], str] | None = None,
) -> list[TrajectoryOutcome]: ...
def report(
    diagnosis: Diagnosis,
    *,
    markers: Sequence[CycleMarker] | None = None,
    read_cycles_out: Callable[[], str] | None = None,
    read_trajectory: Callable[[], str] | None = None,
) -> RecurrenceReport: ...
def parse_merge_commits(
    text: str,
    *,
    merge_pattern: re.Pattern[str] | None = None,
) -> list[MergeCommit]: ...
def observe_git(
    cycles: Sequence[int],
    *,
    merge_commits: Sequence[MergeCommit] | None = None,
    read_git_log: Callable[[], str] | None = None,
) -> GitObservation: ...
def render_final_report(
    diagnosis: Diagnosis,
    *,
    markers: Sequence[CycleMarker] | None = None,
    read_cycles_out: Callable[[], str] | None = None,
    read_trajectory: Callable[[], str] | None = None,
    merge_commits: Sequence[MergeCommit] | None = None,
    read_git_log: Callable[[], str] | None = None,
) -> FinalReport: ...
def render(report: FinalReport) -> str: ...
```

## `revolver.derive`

```python
class DerivationError(Exception): ...

@dataclass(frozen=True)
class ChangeInstruction:
    kind: str
    target: str
    replacement: str
    new_name: str
    evidence: str

@dataclass
class DerivedVariant:
    path: str
    content: str
    predecessor: str
    instruction: ChangeInstruction
    diff_from_predecessor: str
    evidence: str

def derive(
    predecessor: Path | str,
    instruction: ChangeInstruction,
    *,
    read_text: Callable[[Path], str] | None = None,
    compile_check: Callable[[str, str], None] | None = None,
) -> DerivedVariant: ...
```

## `revolver.triple`

```python
TRIPLE_DIR: Path
SEED_REPO: Path
SEED_COMMIT: str
TRIPLE: dict[str, tuple[str, Path]]

class TripleMismatch(Exception): ...

def verify_triple(triple_dir: Path | None = None) -> None: ...
def resolve(name: str, triple_dir: Path | None = None) -> Path: ...
```
