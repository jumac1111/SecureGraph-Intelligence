from pathlib import Path
import secrets

from fastapi import (
    Cookie,
    FastAPI,
    HTTPException,
)

from fastapi.responses import (
    FileResponse,
    JSONResponse,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from pydantic import BaseModel

from app.audit.logger import (
    AuditLogger,
)

from app.config import (
    config,
)

from app.engine.behavior_learning import (
    BehavioralLearningEngine,
)

from app.engine.engine import (
    ContinuousAssuranceEngine,
)

from app.engine.policy import (
    PolicyEngine,
)

from app.models.audit import (
    AuditEvent,
    AuditEventType,
)

from app.models.profile import (
    UserProfile,
)

from app.models.signals import (
    BehaviorObservation,
)

from app.middleware.security_context import (
    SecurityContextMiddleware,
)

from app.storage.session_store import (
    SessionStore,
)


# ==========================================================
# APPLICATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Continuous Assurance",
    version="0.9.0",
)


# ==========================================================
# AUDIT
# ==========================================================

audit_logger = AuditLogger(
    config.audit
)


# ==========================================================
# STORAGE
# ==========================================================

session_store = SessionStore(
    audit_logger=audit_logger,
    config=config.session,
)


# ==========================================================
# SECURITY CONTEXT MIDDLEWARE
# ==========================================================

# Register the geographic/network context validation layer.
#
# IMPORTANT:
# SecurityContextMiddleware no longer accepts max_speed_kmh.
# Travel-velocity policy belongs to the security-context layer
# itself, so passing max_speed_kmh here causes:
#
# TypeError:
# SecurityContextMiddleware.__init__()
# got an unexpected keyword argument 'max_speed_kmh'
#
app.add_middleware(
    SecurityContextMiddleware,
    session_store=session_store,
)


# ==========================================================
# STATIC FILES
# ==========================================================

app.mount(
    "/static",
    StaticFiles(
        directory=(
            BASE_DIR
            / "web"
            / "static"
        ),
    ),
    name="static",
)


# ==========================================================
# DEMO AUTHENTICATION
# ==========================================================

DEMO_USERNAME = "researcher"

DEMO_PASSWORD = "research123"


# ==========================================================
# LEARNING
# ==========================================================

learning_engine = (
    BehavioralLearningEngine(
        required_observations=(
            config.learning.required_observations
        )
    )
)


# ==========================================================
# POLICY
# ==========================================================

policy_engine = PolicyEngine(
    config.policy
)


# ==========================================================
# ASSURANCE
# ==========================================================

assurance_engine = (
    ContinuousAssuranceEngine(
        assurance_config=(
            config.assurance
        ),
        policy_engine=policy_engine,
    )
)


# ==========================================================
# USER PROFILES
# ==========================================================

profiles: dict[
    str,
    UserProfile,
] = {}


# ==========================================================
# REQUEST MODELS
# ==========================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class ReverificationRequest(BaseModel):
    verified: bool


# ==========================================================
# AUDIT HELPER
# ==========================================================

def audit(
    event_type: AuditEventType,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    action: str | None = None,
    reason: str | None = None,
    assurance_score: float | None = None,
    risk_score: float | None = None,
    metadata: dict | None = None,
) -> None:
    audit_logger.record(
        AuditEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            action=action,
            reason=reason,
            assurance_score=assurance_score,
            risk_score=risk_score,
            metadata=metadata or {},
        )
    )


# ==========================================================
# SESSION HELPERS
# ==========================================================

def get_session(
    session_id: str | None,
):
    """
    Resolve an authenticated session.

    This helper only resolves the session object.
    Lifecycle validation is handled separately by
    ensure_valid_session().
    """

    if session_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    session = session_store.get(
        session_id
    )

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid session.",
        )

    return session


def ensure_valid_session(
    session_id: str | None,
):
    """
    Resolve and validate an authenticated session.

    SessionStore owns inactivity expiration and lifecycle
    transitions.

    Locked sessions are rejected here because this helper is
    used by protected operations that require an active
    session.
    """

    session = get_session(
        session_id
    )

    session_store.ensure_valid(
        session
    )

    if session.is_locked:
        raise HTTPException(
            status_code=401,
            detail=(
                "Session is locked. "
                + (
                    session.lock_reason
                    or
                    "Authentication is required."
                )
            ),
        )

    return session


# ==========================================================
# PAGES
# ==========================================================

@app.get("/")
def login_page():
    return FileResponse(
        BASE_DIR
        / "web"
        / "login.html"
    )


@app.get("/dashboard")
def dashboard():
    return FileResponse(
        BASE_DIR
        / "web"
        / "dashboard.html"
    )


# ==========================================================
# LOGIN
# ==========================================================

@app.post("/api/login")
def login(
    request: LoginRequest,
):
    if (
        request.username
        != DEMO_USERNAME
        or request.password
        != DEMO_PASSWORD
    ):
        audit(
            AuditEventType.LOGIN_FAILURE,
            metadata={
                "username": request.username,
            },
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    if request.username not in profiles:
        profiles[
            request.username
        ] = UserProfile(
            user_id=request.username
        )

    profile = profiles[
        request.username
    ]

    session_id = (
        secrets.token_urlsafe(32)
    )

    session_store.create(
        session_id=session_id,
        user_id=request.username,
    )

    audit(
        AuditEventType.LOGIN_SUCCESS,
        user_id=request.username,
        session_id=session_id,
    )

    cookie = (
        f"{config.session.cookie_name}="
        f"{session_id}; "
        f"Path={config.session.session_cookie_path}; "
    )

    if config.session.session_cookie_http_only:
        cookie += "HttpOnly; "

    cookie += (
        f"SameSite="
        f"{config.session.session_cookie_same_site}"
    )

    if config.session.session_cookie_secure:
        cookie += "; Secure"

    return JSONResponse(
        content={
            "authenticated": True,
            "user_id": request.username,
            "profile_state": profile.state,
            "session_status": "active",
        },
        headers={
            "Set-Cookie": cookie,
        },
    )


# ==========================================================
# LOGOUT
# ==========================================================

@app.post("/api/logout")
def logout(
    session_id: str | None = Cookie(
        default=None,
        alias=config.session.cookie_name,
    ),
):
    """
    Explicitly terminate the current authenticated session.

    Logout is terminal for the current session. The server-side
    session is locked and the client session cookie is cleared.
    """

    session = get_session(
        session_id
    )

    session_store.ensure_valid(
        session
    )

    if session.is_locked:
        raise HTTPException(
            status_code=401,
            detail=(
                "Session is locked. "
                + (
                    session.lock_reason
                    or
                    "Authentication is required."
                )
            ),
        )

    session_store.logout(
        session
    )

    response = JSONResponse(
        content={
            "authenticated": False,
            "logged_out": True,
            "session_status": "logged_out",
            "message": (
                "Session logged out successfully."
            ),
        }
    )

    response.delete_cookie(
        key=config.session.cookie_name,
        path=config.session.session_cookie_path,
    )

    return response


# ==========================================================
# SESSION STATUS
# ==========================================================

@app.get("/api/session/status")
def session_status(
    session_id: str | None = Cookie(
        default=None,
        alias=config.session.cookie_name,
    ),
):
    """
    Return the current session state.

    Unlike protected operations, this endpoint deliberately
    allows a locked session to be inspected so the client can
    understand why the session is no longer active.
    """

    session = get_session(
        session_id
    )

    session_store.ensure_valid(
        session
    )

    return {
        "authenticated": (
            session.active
        ),
        "active": (
            session.active
        ),
        "user_id": (
            session.user_id
        ),
        "state": (
            session.state.value
        ),
        "behavior_score": (
            session.behavior_score
        ),
        "assurance_score": (
            session.assurance_score
        ),
        "risk_score": (
            session.risk_score
        ),
        "reverify_count": (
            session.reverify_count
        ),
        "lock_reason": (
            session.lock_reason
        ),
        "created_at": (
            session.created_at
        ),
        "last_activity_at": (
            session.last_activity_at
        ),
        "state_changed_at": (
            session.state_changed_at
        ),
    }


# ==========================================================
# REVERIFICATION
# ==========================================================

@app.post("/api/session/reverify")
def reverify_session(
    request: ReverificationRequest,
    session_id: str | None = Cookie(
        default=None,
        alias=config.session.cookie_name,
    ),
):
    # ======================================================
    # 1. SESSION + EXPIRATION
    # ======================================================

    session = ensure_valid_session(
        session_id
    )

    # ======================================================
    # 2. NOT CURRENTLY REVERIFYING
    # ======================================================

    if not session.requires_reverification:
        return {
            "verified": True,
            "session_state": (
                session.state.value
            ),
            "message": (
                "Session does not currently "
                "require reverification."
            ),
        }

    # ======================================================
    # 3. FAILED VERIFICATION
    # ======================================================

    if not request.verified:
        should_lock = (
            policy_engine
            .should_lock_after_failed_reverification(
                session.reverify_count
            )
        )

        if should_lock:
            reason = (
                "Maximum reverification attempts "
                "exceeded."
            )

            session_store.lock(
                session,
                reason=reason,
            )

            return {
                "verified": False,
                "session_state": (
                    session.state.value
                ),
                "session_active": False,
                "reverify_count": (
                    session.reverify_count
                ),
                "action": "lock",
                "message": (
                    "Reverification failed too many "
                    "times. Session has been locked."
                ),
            }

        session_store.mark_reverify(
            session,
            reason=(
                "Identity verification failed."
            ),
        )

        audit(
            AuditEventType.REVERIFICATION_FAILURE,
            user_id=session.user_id,
            session_id=session.session_id,
            action="reverify",
            reason=(
                "Identity verification failed."
            ),
        )

        return {
            "verified": False,
            "session_state": (
                session.state.value
            ),
            "session_active": (
                session.active
            ),
            "reverify_count": (
                session.reverify_count
            ),
            "action": "reverify",
            "message": (
                "Identity verification failed. "
                "Reverification is still required."
            ),
        }

    # ======================================================
    # 4. SUCCESSFUL VERIFICATION
    # ======================================================

    session_store.activate(
        session,
        reason=(
            "Identity verification successful."
        ),
    )

    audit(
        AuditEventType.REVERIFICATION_SUCCESS,
        user_id=session.user_id,
        session_id=session.session_id,
        action="allow",
        reason=(
            "Identity verification successful."
        ),
    )

    return {
        "verified": True,
        "session_state": (
            session.state.value
        ),
        "session_active": (
            session.active
        ),
        "reverify_count": (
            session.reverify_count
        ),
        "message": (
            "Identity verification "
            "successful. Session restored."
        ),
    }


# ==========================================================
# PROTECTED RESOURCE
# ==========================================================

@app.get("/api/protected/resource")
def protected_resource(
    session_id: str | None = Cookie(
        default=None,
        alias=config.session.cookie_name,
    ),
):
    # ======================================================
    # 1. SESSION + EXPIRATION
    # ======================================================

    session = ensure_valid_session(
        session_id
    )

    # ======================================================
    # 2. REVERIFICATION
    # ======================================================

    if session.requires_reverification:
        raise HTTPException(
            status_code=403,
            detail=(
                "Identity verification required "
                "before accessing this resource."
            ),
        )

    # ======================================================
    # 3. ACTIVITY
    # ======================================================

    session_store.touch(
        session
    )

    # ======================================================
    # 4. AUDIT
    # ======================================================

    audit(
        AuditEventType.PROTECTED_RESOURCE_ACCESS,
        user_id=session.user_id,
        session_id=session.session_id,
        action="allow",
    )

    return {
        "authorized": True,
        "resource": "protected",
        "message": (
            "Protected resource accessed "
            "successfully."
        ),
        "user_id": session.user_id,
        "session_state": (
            session.state.value
        ),
    }


# ==========================================================
# BEHAVIOR OBSERVATION
# ==========================================================

@app.post("/api/behavior/observation")
def behavior_observation(
    observation: BehaviorObservation,
    session_id: str | None = Cookie(
        default=None,
        alias=config.session.cookie_name,
    ),
):
    # ======================================================
    # 1. SESSION + EXPIRATION
    # ======================================================

    session = ensure_valid_session(
        session_id
    )

    # ======================================================
    # 2. REVERIFICATION
    # ======================================================

    if session.requires_reverification:
        raise HTTPException(
            status_code=403,
            detail=(
                "Identity verification required "
                "before submitting behavior."
            ),
        )

    # ======================================================
    # 3. ACTIVITY
    # ======================================================

    session_store.touch(
        session
    )

    # ======================================================
    # 4. PROFILE
    # ======================================================

    user_id = session.user_id

    if user_id not in profiles:
        profiles[user_id] = UserProfile(
            user_id=user_id
        )

    profile = profiles[
        user_id
    ]

    # ======================================================
    # 5. AUDIT OBSERVATION
    # ======================================================

    audit(
        AuditEventType.BEHAVIOR_OBSERVATION,
        user_id=user_id,
        session_id=session.session_id,
        metadata={
            "profile_state": str(
                profile.state
            ),
        },
    )

    # ======================================================
    # 6. LEARNING
    # ======================================================

    if profile.state != "established":
        profile = (
            learning_engine.update_profile(
                profile,
                observation,
            )
        )

        profiles[user_id] = profile

        progress = (
            profile.observation_count
            /
            profile.required_observations
        )

        progress = min(
            progress,
            1.0,
        )

        return {
            "mode": "learning",
            "profile_state": (
                profile.state
            ),
            "observation_count": (
                profile.observation_count
            ),
            "required_observations": (
                profile.required_observations
            ),
            "progress": progress,
            "behavior_score": None,
            "assurance_score": None,
            "risk_score": None,
            "action": "learning",
            "session_state": (
                session.state.value
            ),
            "session_active": (
                session.active
            ),
            "reason": (
                "Behavioral profile is still "
                "being established."
            ),
        }

    # ======================================================
    # 7. ASSURANCE + POLICY
    # ======================================================

    decision = (
        assurance_engine.evaluate(
            profile,
            observation,
        )
    )

    # ======================================================
    # 8. STORE SCORES
    # ======================================================

    session.behavior_score = (
        decision.behavior_score
    )

    session.assurance_score = (
        decision.assurance_score
    )

    session.risk_score = (
        decision.risk_score
    )

    # ======================================================
    # 9. AUDIT ASSURANCE
    # ======================================================

    audit(
        AuditEventType.ASSURANCE_EVALUATED,
        user_id=user_id,
        session_id=session.session_id,
        action=decision.action.value,
        reason=decision.reason,
        assurance_score=(
            decision.assurance_score
        ),
        risk_score=(
            decision.risk_score
        ),
    )

    # ======================================================
    # 10. APPLY POLICY
    # ======================================================

    session_store.apply_action(
        session,
        decision.action,
        decision.reason,
    )

    # ======================================================
    # 11. RESPONSE
    # ======================================================

    return {
        "mode": "verification",
        "profile_state": (
            profile.state
        ),
        "observation_count": (
            profile.observation_count
        ),
        "behavior_score": (
            decision.behavior_score
        ),
        "face_score": (
            decision.face_score
        ),
        "context_score": (
            decision.context_score
        ),
        "assurance_score": (
            decision.assurance_score
        ),
        "risk_score": (
            decision.risk_score
        ),
        "action": (
            decision.action.value
        ),
        "session_state": (
            session.state.value
        ),
        "session_active": (
            session.active
        ),
        "reverify_count": (
            session.reverify_count
        ),
        "reason": (
            decision.reason
        ),
    }
