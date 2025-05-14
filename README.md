# sales_development_agent
# Sales Development Agent 

> [An AI-powered agent to automate and supercharge your sales development pipeline, from lead enrichment to personalized outreach.]

---

## 🌟 Overview

Welcome to the Sales Development Agent! This project aims to autoamte lead generation from industry event and association information for outreach. 

This agent implements an end-to-end pipeline, from scraping a lead lists togenerating tailored email drafts, all accessible through a user-friendly interface built with Streamlit and powered by the capabilities of the Langchain framework.

---

## ✨ Features

* **🤖 End-to-End Automated Pipeline:** Fully automated workflow for lead processing, enrichment, and initial outreach preparation. Describe the stages: e.g., Data Ingestion -> Lead Cleaning -> Data Enrichment (e.g., finding contact details, company info) -> ICP-based Segmentation -> Personalized Content Generation]
* **🧠 Langchain-Powered Intelligence:** Utilizes Large Language Models (LLMs) via Langchain for tasks such as:
    * Automated research and summarization of lead/company information.
    * Generating personalized email copy, subject lines, and call scripts.
    * Understanding and classifying lead intent or interest.]
* **🖥️ Interactive Streamlit UI (v1):** An intuitive web interface that allows users to:
    * Upload and manage lead lists.
    * Configure agent parameters and campaign settings.
    * Monitor the pipeline's progress.
    * Review content before using for sending.
    * View analytics and reports (Future)
    ---

## Tech Stack

* **Core:** Python [Specify version, e.g., 3.9+]
* **AI/LLM Framework:** Langchain
* **Web UI:** Streamlit
* **Data Handling:** Pandas, NumPy
* **APIs Used:** OpenAI API, Google Search API, specific lead enrichment APIs - palceholder
* **Database:** SQLite, PostgreSQL (for scale)
* **Development Tools:** Git, VS Code

---
## Prerequisites

Before you begin, ensure you have the following installed:

* **Python:** Version [e.g., 3.9, 3.10, or 3.11]. You can download it from [python.org](https://www.python.org/).
* **pip:** (Python package installer) Usually comes with Python.
* **Git:** For cloning the repository. Download from [git-scm.com](https://git-scm.com/).
* **Virtual Environment Tool:** `venv` (recommended, comes with Python) or `conda`.
* **API Keys (User Provided):**
    * [e.g., OpenAI API Key]: Required for [Langchain LLM functionalities]. You'll need to set this as an environment variable.
    * [e.g., Other API keys for lead enrichment, search, etc.]: Specify which ones and for what purpose.
---

## Installation & Setup

1.  **Clone the Repository:**
    Open your terminal or command prompt and run:
    ```bash
    git clone [https://github.com/sangwanaakanksha/sales_development_agent.git](https://github.com/sangwanaakanksha/sales_development_agent.git)
    cd sales_development_agent
    ```

2.  **Create and Activate a Virtual Environment:**
    This keeps your project dependencies isolated.
    ```bash
    python -m venv venv
    ```
    * On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    * On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    You should see `(venv)` at the beginning of your terminal prompt.

3.  **Install Dependencies:**
    Install all required Python packages using the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
    *(If you haven't created this file yet, do it now from your activated virtual environment after installing all necessary packages: `pip freeze > requirements.txt` and commit it to your repository.)*

4.  **Set Up Environment Variables:**
    This project requires API keys and potentially other configuration settings to be stored as environment variables for security and flexibility.
    * Create a new file named `.env` in the root project directory (this file is gitignored by default if you add `.env` to your `.gitignore` file - **DO THIS!**).
    * Copy the contents of `.env.example` (if you provide one) or add the following format to your `.env` file:
        ```env
        # .env file
        OPENAI_API_KEY="your_openai_api_key_here"
        # ANOTHER_API_KEY="your_other_api_key_here"
        # DATABASE_URL="your_database_url_if_needed"
        # OTHER_CONFIG_SETTING="value"
        ```
    * Replace `"your_..._key_here"` with your actual credentials.
    * **Important:** The application will load these variables at runtime. Ensure the `.env` file is present and correctly formatted.
    ```

---

## ▶️ Usage

1.  **Ensure your virtual environment is activated** and your `.env` file is correctly set up.

2.  **Run the Run.Py Application:**
    Navigate to the project's root directory in your terminal and execute:
    ```bash
    python run.py
    ```
    Enter user prompted inputs such as trade show - default ISA2025, number of companies to source, custom email sender's signature

3.  **Access the Streamlit UI:**
    Streamlit will typically provide a local URL in the terminal (usually `http://localhost:8501`). Open this URL in your web browser.

4.  **Using the Agent:**
    * Execute run.py to trigger search agent 

---

## 📂 Project Structure
sales_development_agent/
│
├── .venv/                       # Virtual environment directory (gitignored)
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Example environment variables file
├── .gitignore                   # Specifies intentionally untracked files that Git should ignore
├── README.md                    # This file
└── config.py                    # Configuration loading
├── requirements.txt             # Project dependencies
├── app.py                       # Main Streamlit application script
├── util/                         # Or your main package name (e.g., util/)
│   ├── init.py
│   ├── database.py              # Databse logging
│   |── enrichment.py
    |── finalize.py
    |── search.py
  │   └── [e.g., pipeline.py, llm_utils.py, data_processor.py]
    |── outreach.py
    |── guardrail.py

