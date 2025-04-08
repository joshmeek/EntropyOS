from fastapi import FastAPI
from contextlib import asynccontextmanager

# Placeholder for API routers
# from .api.routes import simulation, agents # Example
from app.api import agent_routes # Import the agent router
from app.api import simulation_routes # <-- Import simulation router
from app.core.llm_client import init_llm_client # Import the init function

# Define lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("INFO:     Application startup...")
    init_llm_client() # Initialize LLM client
    print("INFO:     Application startup complete.")
    yield
    # Shutdown
    print("INFO:     Application shutdown...")
    # Add any cleanup logic here if needed
    print("INFO:     Application shutdown complete.")

app = FastAPI(title="EntropyOS API", version="0.1.0", lifespan=lifespan)

@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# Include routers here later
# app.include_router(simulation.router, prefix="/simulation", tags=["Simulation"])
# app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(simulation_routes.router, prefix="/simulations", tags=["Simulations"]) # <-- Include simulation routes
app.include_router(agent_routes.router, prefix="/agents", tags=["Agents"]) # Include agent routes

# Add WebSocket endpoint later for logs 