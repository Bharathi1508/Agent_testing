from app.api.routes.live_assurance_dashboard import router as live_assurance_router

"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Main FastAPI Application

Features:
1. Metadata Agent
2. Intelligent Metadata Agent
3. SQL Agent
4. Agent Registry
5. Agent Assurance
6. Governance Approval
7. Dynamic Supervisor
8. Dynamic Agent Onboarding
9. Automatic Configuration Assurance
10. Next.js Frontend Integration
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==========================================
# LangGraph Agents
# ==========================================

from app.graphs.metadata_graph import graph
from app.graphs.supervisor_graph import supervisor_graph

# ==========================================
# Existing Services
# ==========================================

from app.services.question_parser import parse_question

# ==========================================
# Phase 12 - Assurance Engine
# ==========================================

from app.services.assurance_engine import (
    run_assurance,
)

# ==========================================
# Existing API Routers
# ==========================================

from app.api.routes.sql_routes import (
    router as sql_router,
)

from app.api.routes.registry_routes import (
    router as registry_router,
)

from app.api.routes.assurance_routes import (
    router as assurance_router,
)
from app.api.routes.assurance_dashboard import (
    router as assurance_dashboard_router,
)


from app.api.routes.approval_routes import (
    router as approval_router,
)

from app.api.routes.dynamic_supervisor_routes import (
    router as dynamic_supervisor_router,
)

# ==========================================
# Dynamic Agent Onboarding
# ==========================================

from app.api.routes.onboarding import (
    router as onboarding_router,
    configure_onboarding_service,
)

from app.discovery.manifest_validator import (
    validate_discovered_agent,
)

from app.discovery.onboarding_dependencies import (
    create_onboarding_service,
)


# ==========================================
# Initialize FastAPI
# ==========================================

app = FastAPI(
    title="HEAAP - Hybrid Enterprise Agent Assurance Platform",
    description=(
        "Hybrid enterprise platform for "
        "agent registration, execution, "
        "assurance testing, governance, "
        "dynamic discovery and onboarding."
    ),
    version="1.2.0",
)

from app.api.routes.supervisor_metadata_routes import router as heaap_question_supervisor_router
app.include_router(heaap_question_supervisor_router)


# ==========================================
# Configure CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Phase 12 - Configure Onboarding
# ==========================================

onboarding_service = create_onboarding_service(
    validator=validate_discovered_agent,
    assurance_runner=run_assurance,
)

configure_onboarding_service(
    onboarding_service
)


# ==========================================
# Register API Routers
# ==========================================

app.include_router(sql_router)

app.include_router(registry_router)

app.include_router(assurance_router)
app.include_router(assurance_dashboard_router)
app.include_router(live_assurance_router)

app.include_router(approval_router)

app.include_router(dynamic_supervisor_router)

app.include_router(onboarding_router)


# ==========================================
# Home Endpoint
# ==========================================

@app.get(
    "/",
    tags=["System"],
)
def home():
    return {
        "status": "running",
        "application": "HEAAP",
        "version": "1.2.0",
        "agents": [
            "metadata_agent",
            "sql_agent",
        ],
        "features": [
            "agent_registry",
            "agent_assurance",
            "governance",
            "dynamic_supervisor",
            "dynamic_onboarding",
            "automatic_configuration_assurance",
        ],
    }


# ==========================================
# Health Endpoint
# ==========================================

@app.get(
    "/health",
    tags=["System"],
)
def health():
    return {
        "status": "healthy",
        "application": "HEAAP",
        "onboarding": "configured",
        "assurance": "configuration_engine_connected",
    }


# ==========================================
# Metadata Agent Request Models
# ==========================================

class MetadataRequest(BaseModel):

    action: str

    table_name: Optional[str] = None

    column_name: Optional[str] = None


class QuestionRequest(BaseModel):

    question: str


class IntelligentQuestionRequest(BaseModel):

    question: str


# ==========================================
# Metadata Agent - Direct Execution
# ==========================================

@app.post(
    "/metadata/run",
    tags=["Metadata Agent"],
)
def run_metadata(
    request: MetadataRequest,
):

    if (
        request.action in (
            "describe_table",
            "list_columns",
        )
        and not request.table_name
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "table_name is required "
                "for this action."
            ),
        )

    if (
        request.action == "describe_column"
        and (
            not request.table_name
            or not request.column_name
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "table_name and column_name "
                "are required."
            ),
        )

    return graph.invoke(
        request.model_dump(
            exclude_none=True
        )
    )


# ==========================================
# Metadata Agent - Rule-Based Questions
# ==========================================

@app.post(
    "/metadata/ask",
    tags=["Metadata Agent"],
)
def ask_metadata(
    request: QuestionRequest,
):

    parsed = parse_question(
        request.question
    )

    if parsed["action"] == "unsupported":
        return {
            "status": "unsupported",
            "message": parsed["message"],
        }

    return graph.invoke(parsed)


# ==========================================
# Metadata Agent - AI Questions
# ==========================================

@app.post(
    "/metadata/ask-ai",
    tags=["Metadata Agent"],
)
def ask_intelligent_metadata(
    request: IntelligentQuestionRequest,
):

    from app.graphs.intelligent_metadata_graph import (
        intelligent_graph,
    )

    result = intelligent_graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": request.question,
                }
            ]
        }
    )

    return {
        "status": "success",
        "answer": result["messages"][-1].content,
    }


# ==========================================
# Supervisor Request Model
# ==========================================

class SupervisorRequest(BaseModel):

    agent_type: str

    action: str

    table_name: Optional[str] = None

    column_name: Optional[str] = None

    limit: int = Field(
        default=5,
        ge=1,
        le=100,
    )


# ==========================================
# Supervisor Agent - Direct Execution
# ==========================================

@app.post(
    "/supervisor/run",
    tags=["Supervisor"],
)
def run_supervisor(
    request: SupervisorRequest,
):

    return supervisor_graph.invoke(
        request.model_dump(
            exclude_none=True
        )
    )


# Dynamic Gold Metadata Assurance
from app.api.routes.dynamic_metadata_assurance_routes import (
    router as dynamic_metadata_assurance_router,
)
app.include_router(dynamic_metadata_assurance_router)

from app.api.routes.business_question_routes import router as business_question_router
app.include_router(business_question_router)


# Supervisor Metadata Selection
from app.api.routes.supervisor_metadata_routes import (
    router as supervisor_metadata_router,
)
app.include_router(supervisor_metadata_router)


# Register HEAAP Supervisor Metadata routes
from app.api.routes.supervisor_metadata_routes import (
    router as heaap_metadata_validation_router,
)

app.include_router(heaap_metadata_validation_router)


# Register bulk metadata assurance endpoint
from app.api.routes.supervisor_metadata_routes import (
    bulk_validate_metadata,
    BulkMetadataRequest,
)

app.add_api_route(
    "/api/supervisor-metadata/bulk-validate",
    bulk_validate_metadata,
    methods=["POST"],
    response_model=None,
)
