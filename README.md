# EntropyOS

*Model the world, before you change it*

> **Note:** This project is **lightly, actively maintained**. Everything is subject to change.

## Overview

EntropyOS is an agent-based simulation engine designed to model societal, economic, and behavioral dynamics in response to various events (e.g., policy changes, technological shifts). It provides a controlled environment to study how entropy—disorder, divergence, or systemic unpredictability can emerge within a population over time.

Agents within the simulation are driven by Large Language Models (LLMs), allowing them to adapt their behavior based on memory, environmental context, and social interactions.

## Core Technologies

*   **Backend:** Python (FastAPI)
*   **Database:** PostgreSQL + pgvector extension
*   **Agent LLM:** Google Gemini (planning to support others in the future)
*   **Orchestration:** Docker Compose

*(Frontend using React/TypeScript is planned)*

## Current Status & Key Features

*   **Backend API:** Core endpoints for managing simulations (CRUD), agents (CRUD, LTM query), events (injection), and metrics (retrieval) are implemented
*   **Agent System:** Agent schema defined (demographics, traits, beliefs, memory). Seeding service implemented to generate populations
*   **LLM Integration:** Synchronous LLM calls (Gemini) integrated into the simulation tick for agent decision-making. Includes structured prompting and response parsing
*   **Simulation Engine:** A synchronous tick execution loop is functional within the backend API. It processes events, runs agent LLM updates, calculates basic metrics, and advances the simulation state
*   **Entropy Metrics:** Basic metrics (Gini Coefficient, Belief Variance) are calculated and stored per tick
*   **Vector Store:** pgvector is set up for storing and querying long-term memory embeddings (LTM implementation in progress)

*(Asynchronous task processing and a full frontend UI are planned for future development)*

## MVP Goal

Deliver a working proof-of-concept simulating the effect of a single event (Universal Basic Income) on a small town population (100+ agents) over several simulated months, visualizing the resulting changes in entropy metrics (Gini, belief variance)

## Getting Started

### Prerequisites

*   Docker and Docker Compose
*   Git
*   A Google Gemini API Key

### Setup

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:joshmeek/EntropyOS.git
    cd EntropyOS
    ```

2.  **Configure Environment:**
    *   Copy the example environment file: `cp .env.example .env`
    *   Edit the `.env` file and add your `GEMINI_API_KEY`. Adjust other variables like database credentials or ports if necessary

3.  **Build and Run Services:**
    ```bash
    docker compose up --build -d
    ```
    This will build the necessary Docker images and start the backend API, database, and other services in detached mode

4.  **Database Migrations:**
    Apply database schema changes:
    ```bash
    docker compose exec backend alembic upgrade head
    ```

5.  **Access the API:**
    The FastAPI backend should now be running. You can access the interactive API documentation (Swagger UI) typically at `http://localhost:8000/docs` (adjust the port if you changed it in `.env`)

### Running a Simulation (Example Script)

A basic script is provided to demonstrate creating a simulation, seeding agents, injecting a UBI event, running ticks, and reporting metrics:

```bash
python backend/app/scripts/run.py
```
*(Note: This script currently includes delays to manage API rate limits and may run slowly).*

## Next Steps / Roadmap

*   Implement Frontend UI (Dashboard, Visualizations, Agent Inspector)
*   Integrate Asynchronous Task Processing (e.g., Hatchet) for scalable LLM calls and tick execution
*   Implement Long-Term Memory embedding and retrieval
*   Develop more sophisticated Event types and a Workflow system
*   Expand Entropy Metrics
*   Add unit and integration tests

## Contributing

As this project is in flight, feel free to reach out if you want to discuss anything [https://josh.dev](https://josh.dev).

## License

This project is licensed under the MIT License - see the LICENSE file for details.