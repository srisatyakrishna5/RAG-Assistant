# 🧪 Lab Manual — RAG Document Assistant
### Step-by-Step Setup Guide for Non-Technical Users

---

## Welcome

This lab manual walks you through every single step needed to install and run the **RAG Document Assistant** on your personal computer — even if you have never written a line of code.

By the end of this guide, you will have a working web application that lets you upload any PDF and ask questions about its contents in plain language.

**What you will need:**
- A computer running Windows 10/11, macOS, or Linux
- An internet connection
- An Azure account (free trial is fine)
- About 60–90 minutes of uninterrupted time

---

## Part 1 — Understanding What We Are Building

Before we start, here is a simple explanation of what the app does:

1. **You upload a PDF.** The app reads every page and extracts the text.
2. **The text is broken into small pieces** (called "chunks") and stored in a searchable database on Azure.
3. **You type a question.** The app finds the most relevant pieces of text from your PDF.
4. **An AI (GPT-4.1) reads those pieces** and writes you a direct answer, telling you exactly which pages the information came from.

No information is stored on any third-party service — everything goes to your own private Azure account.

---

## Part 2 — Setting Up Your Azure Account

> **If you already have an Azure account, skip to Step 2.3.**

### Step 2.1 — Create a Free Azure Account

1. Open your web browser and go to **https://azure.microsoft.com/free**
2. Click the blue **"Start free"** button.
3. Sign in with a Microsoft account (Outlook, Hotmail, or any @microsoft.com address).  If you do not have one, click "Create one" on the sign-in page.
4. Complete the registration form.  You will need:
   - A phone number (for verification)
   - A credit card (it will NOT be charged for free-tier services)
5. Agree to the terms and click **"Sign up"**.
6. You will land on the Azure Portal dashboard at **https://portal.azure.com**.

### Step 2.2 — Familiarise Yourself with the Azure Portal

The Azure Portal is the web interface where you create and manage all Azure services.  Key things to know:

- The **search bar** at the top lets you find any service by name.
- **Resource groups** are like folders that hold related services together.
- Every service has a **"Keys and Endpoint"** or **"Keys"** section in the left menu — this is where you find the credentials (keys) needed to connect the app to that service.

### Step 2.3 — Create a Resource Group

A resource group keeps all the services for this project organised together.

1. In the Azure Portal, type **"Resource groups"** in the search bar and click the result.
2. Click **"+ Create"** in the top-left corner.
3. Fill in:
   - **Subscription:** Select your subscription (usually "Azure subscription 1" for free accounts).
   - **Resource group name:** Type `document-advisor-rg`
   - **Region:** Select the region closest to you (e.g., East US, West Europe).
4. Click **"Review + Create"**, then **"Create"**.

---

## Part 3 — Creating Azure Services

You need to create **four Azure services** (one of which is a Microsoft Foundry project with model deployments).  Follow the steps below for each one.

---

### Step 3.1 — Create Azure Document Intelligence

This service reads your PDF and extracts the text from every page.

1. In the Azure Portal search bar, type **"Document Intelligence"** and click **"Document Intelligence"** in the results.
2. Click **"+ Create"**.
3. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `document-advisor-rg`
   - **Region:** Same region you chose earlier
   - **Name:** Type a unique name, e.g., `doc-intel-yourname`
   - **Pricing tier:** Select **"Free F0"** (allows 500 pages/month free)
4. Click **"Review + Create"**, then **"Create"**.
5. Wait for the deployment to finish (green check mark).  Click **"Go to resource"**.
6. In the left menu, click **"Keys and Endpoint"**.
7. **Copy and save in a text file:**
   - **Endpoint** (e.g., `https://doc-intel-yourname.cognitiveservices.azure.com/`)
   - **KEY 1** (a long string of letters and numbers)

---

### Step 3.2 — Create Azure AI Search

This is the searchable database where your document chunks will be stored.

1. In the search bar, type **"AI Search"** and click **"AI Search"**.
2. Click **"+ Create"**.
3. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `document-advisor-rg`
   - **Service name:** Type a unique name, e.g., `search-yourname` (must be lowercase, no spaces)
   - **Location:** Same region
   - **Pricing tier:** Click "Change Pricing Tier" and select **"Free"**
4. Click **"Review + Create"**, then **"Create"**.
5. Wait for deployment.  Click **"Go to resource"**.
6. In the left menu, click **"Keys"**.
7. **Copy and save:**
   - **Url** (shown at the top of the Overview page, e.g., `https://search-yourname.search.windows.net`)
   - **Primary admin key** (from the Keys page)

---

### Step 3.3 — Create a Microsoft Foundry Project and Deploy Models

Instead of creating a standalone Azure OpenAI resource, you will use **Microsoft Foundry**.  Foundry is the unified platform that brings together AI models, agents, and tools under a single Azure resource — it hosts your model deployments and provides a single project endpoint and API key for both GPT-4.1 and embeddings.

At the heart of every generative AI app or agent, there is a language model — usually a large language model (LLM).  Microsoft Foundry provides a large collection of models from Microsoft, OpenAI, and other providers that you can deploy and use in your AI apps and agents.

> **Terminology note:** Microsoft Foundry was previously known as "Azure AI Foundry" and "Azure AI Studio".  The current documentation and portal use the name **Microsoft Foundry**.  If you see references to the older names elsewhere, they refer to the same service.

> **Note:** Many components of Microsoft Foundry, including the Microsoft Foundry portal, are subject to continual development.  This reflects the fast-moving nature of artificial intelligence technology.  Some elements of your user experience may differ from the descriptions in this guide.

#### Step 3.3a — Open the Microsoft Foundry Portal

1. Open your browser and go to **https://ai.azure.com**.
2. Sign in with the same Microsoft account you used for the Azure Portal.
3. Close any **tips or quick-start panes** that appear the first time you sign in.  If necessary, use the **Foundry logo** at the top left to navigate to the home page.
4. If you see a **"New Foundry"** toggle in the toolbar at the top of the page, make sure it is **turned on**.  These instructions refer to the new Foundry experience.
5. You will land on the **Microsoft Foundry** home page.

#### Step 3.3b — Create a New Foundry Project

A Foundry **project** organises your work — model deployments, agents, evaluations, and files — under a single **Foundry resource** in Azure.

1. In the upper-left corner of the portal, click the **project name** dropdown (it may say "Select a project" if this is your first time).
2. Click **"Create new project"**.
3. Enter a **project name**, e.g., `document-advisor-project`.
4. *(Optional — Advanced options)* Click **"Advanced options"** if you want to customise:
   - **Foundry resource:** Enter a valid name for your AI Foundry resource (or let the portal auto-create one).
   - **Subscription:** Your Azure subscription.
   - **Resource group:** Select `document-advisor-rg` (the one you created in Step 2.3), or create/select a resource group.
   - **Region:** Select any of the **AI Foundry recommended regions** — **"East US"** or **"East US 2"** have the widest model availability.
   - The portal will automatically create a **Foundry resource** for you when you create the project.  You do not need to create one separately.
5. Click **"Create project"**.
6. Wait for provisioning to complete (1–3 minutes).  You will be taken to the project **Home** page.

#### Step 3.3c — Find Your Project Endpoint and Key

1. On the project **Home** page, you will see your **project endpoint** and **API key** displayed.
2. The endpoint looks like `https://YOUR-RESOURCE-NAME.openai.azure.com/` or `https://YOUR-RESOURCE-NAME.services.ai.azure.com/`.
3. **Copy and save in your text file:**
   - **Project endpoint** (the full URL shown on the Home page)
   - **API key** (click the copy icon next to it)

> **Note:** You do not need an API key if you use Microsoft Entra ID authentication, but for this lab we use the API key approach for simplicity.  This endpoint and key work for both GPT-4.1 and the embedding model — you do not need separate credentials.
>
> **Authentication options:** Microsoft Foundry supports two authentication methods:
> - **Key-based authentication:** The client app presents a security key (simplest approach — used in this lab).
> - **Microsoft Entra ID authentication:** The client app presents an authentication token based on an identity assigned to it or to the current user (recommended for production).

#### Step 3.3d — Deploy the GPT-4.1 Model

1. From the project Home page, select **"Find models"** (or on the **Discover** page, select the **Models** tab) to view the Microsoft Foundry **model catalog**.
2. In the search box, type **"gpt-4.1"** and press Enter.
3. Click **"gpt-4.1"** from the results list to open the model card, which describes its features and capabilities.
4. Click **"Deploy"** → **"Custom settings"** (or choose **"Default settings"** for the quickest setup).
5. Fill in the deployment details:
   - **Deployment name:** Type exactly `gpt-4.1`
   - **Deployment type:** Select **"Global Standard"** (recommended — gives the highest quota and broadest availability)
   - **Tokens per minute rate limit:** The default is fine for this lab (you can increase later if needed)
6. Click **"Deploy"**.
7. Wait for the deployment to complete (usually under 1 minute).  You will land on the **model playground** where you can test the model immediately.

> **Tip — Insufficient quota?** Model deployments are subject to regional quotas.  If you don't have enough quota to deploy `gpt-4.1` in your project's region, you can use a different model — such as **gpt-4.1-mini**, **gpt-4.1-nano**, or **gpt-4o-mini**.  Alternatively, create a new project in a different region.  Update the `AZURE_OPENAI_DEPLOYMENT` value in your `.env` file to match the deployment name you chose.

#### Step 3.3e — Test the Model in the Playground (Optional)

The model playground lets you chat with your deployed model and experiment with settings before connecting it to the application.

1. In the **Chat** pane of the playground, enter a prompt such as `Who was Ada Lovelace?` and review the response.
2. Enter a follow-up prompt, such as `Tell me more about her work with Charles Babbage.` — the model retains conversation context between messages.
3. Use the **New chat** button (top-right of the chat pane) to restart the conversation and clear history.
4. **Experiment with system prompts:** In the left pane, find the **Instructions** text area and change the system prompt — e.g., `You are an AI assistant that provides short and concise answers using simple language. Limit responses to a single sentence.`  Then try the same prompt and observe the difference.
5. **Experiment with parameters:** Next to the model name in the left pane, select **Parameters**.  Review the settings (use the **(i)** links for descriptions).  Changing the **Temperature** modifies randomness — lower values produce more deterministic responses, higher values produce more creative ones.
6. When finished experimenting, reset the instructions and parameters to their defaults.

> **Tip:** Use the **Stop generation** button in the chat pane to halt long-running responses.

#### Step 3.3f — Deploy the Embedding Model

1. Navigate back to the model catalog: click **"Discover"** in the upper-right navigation, then **"Models"** in the left pane.
2. Search for **"text-embedding-ada-002"** and click it.
3. Click **"Deploy"** → **"Custom settings"**.
4. Fill in:
   - **Deployment name:** Type exactly `text-embedding-ada-002`
   - **Deployment type:** Select **"Standard"**
5. Click **"Deploy"**.
6. Once the deployment completes, both models are ready.

#### Step 3.3g — Verify Your Deployments

1. In the upper-right navigation, click **"Build"**, then select **"Models"** in the left pane to see all deployments on your Foundry resource.
2. Confirm you see two deployments:
   - `gpt-4.1` — Status: **Succeeded**
   - `text-embedding-ada-002` — Status: **Succeeded**
3. If either shows a failure, click on it to see the error.  Common issues:
   - **Insufficient quota:** Try a different region or select a lower tokens-per-minute rate limit.  You can request more quota via the [quota increase form](https://aka.ms/oai/stuquotarequest).
   - **Model not available in region:** Go back to Step 3.3b and create a new project in **East US** or **East US 2**.

#### Step 3.3h — View Client Code (Optional)

The playground provides sample code that a client application can use to chat with the deployed model.

1. In the model playground **Chat** pane, select the **Code** tab.
2. Choose the following code preferences:
   - **API:** Responses API (the newer syntax offering greater flexibility for apps and agents)
   - **Language:** Python
   - **SDK:** OpenAI SDK
   - **Authentication:** Key authentication
3. The resulting sample should look similar to the following:

   ```python
   from openai import OpenAI

   endpoint = "https://your-project-resource.openai.azure.com/openai/v1/"
   deployment_name = "gpt-4.1"
   api_key = "<your-api-key>"

   client = OpenAI(
       base_url=endpoint,
       api_key=api_key
   )

   response = client.responses.create(
       model=deployment_name,
       input="What is the capital of France?",
   )

   print(f"answer: {response.output[0]}")
   ```

   The code connects to the resource endpoint for your Microsoft Foundry project, using its secret authentication key, and uses your deployed model to generate a response from an input prompt.

> **Note:** The **Completions** API is the broadly used programmatic syntax.  The **Responses** API is a newer syntax that offers greater flexibility for building apps that converse with both standalone models and agents.  Both are supported.  Our application (`app.py`) uses the Chat Completions API.

4. Switch back to the **Chat** tab when you have finished reviewing the code.

---

### Step 3.4 — Create Azure Speech Service (Optional)

This service enables voice input and spoken answers.  Skip this step if you only want text-based chat.

1. In the search bar, type **"Speech"** and click **"Speech services"**.
2. Click **"+ Create"**.
3. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `document-advisor-rg`
   - **Region:** Same region
   - **Name:** Type a unique name, e.g., `speech-yourname`
   - **Pricing tier:** **Free F0**
4. Click **"Review + Create"**, then **"Create"**.
5. Go to the resource → **"Keys and Endpoint"**.
6. **Copy and save:**
   - **KEY 1**
   - **Location/Region** (e.g., `eastus`)

---

### Step 3.5 — Create Azure Translator (Optional)

This service translates answers into Hindi, French, or Telugu.  Skip this step if you only need English output.

1. In the search bar, type **"Translator"** and click **"Translator"**.
2. Click **"+ Create"**.
3. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `document-advisor-rg`
   - **Region:** Select **"Global"**
   - **Name:** Type a unique name, e.g., `translator-yourname`
   - **Pricing tier:** **Free F0**
4. Click **"Review + Create"**, then **"Create"**.
5. Go to the resource → **"Keys and Endpoint"**.
6. **Copy and save:**
   - **KEY 1**
   - **Text Translation** → **Region** (e.g., `global`)

---

## Part 4 — Installing Python

Python is the programming language the app is written in.  You need to install it on your computer.

### Step 4.1 — Download Python

1. Open your browser and go to **https://www.python.org/downloads/**
2. Click the large yellow button **"Download Python 3.x.x"** (any version 3.10 or higher is fine).

### Step 4.2 — Install Python on Windows

1. Run the downloaded installer (`.exe` file).
2. **VERY IMPORTANT:** On the first screen, check the box **"Add Python to PATH"** at the bottom.  Without this, nothing will work.
3. Click **"Install Now"**.
4. Wait for installation to complete.  Click **"Close"**.

### Step 4.3 — Install Python on macOS

1. Run the downloaded `.pkg` installer.
2. Follow the on-screen prompts and click "Continue" through all screens.
3. Click "Install".

### Step 4.4 — Verify Python is Installed

1. Open a **terminal** (Command Prompt on Windows, Terminal on macOS/Linux).
   - **Windows:** Press `Win + R`, type `cmd`, press Enter.
   - **macOS:** Press `Cmd + Space`, type `Terminal`, press Enter.
2. Type the following and press Enter:
   ```
   python --version
   ```
   You should see something like `Python 3.12.0`.  If you see an error, try `python3 --version`.

---

## Part 5 — Downloading the Application

### Step 5.1 — Download the Code

**If you have Git installed:**
```
git clone <repository-url>
cd document-advisor
```

**If you do NOT have Git:**
1. Go to the repository page in your browser.
2. Click the green **"Code"** button → **"Download ZIP"**.
3. Extract the ZIP file to a convenient location (e.g., `C:\Users\YourName\document-advisor` on Windows, or `~/document-advisor` on macOS).

### Step 5.2 — Open a Terminal in the Project Folder

**Windows:**
1. Open File Explorer.
2. Navigate to the `document-advisor` folder.
3. Hold `Shift` and right-click inside the folder (not on a file).
4. Click **"Open PowerShell window here"** or **"Open Command Prompt here"**.

**macOS:**
1. Open Terminal.
2. Type `cd ` (with a space after `cd`), then drag the `document-advisor` folder from Finder into the Terminal window. Press Enter.

---

## Part 6 — Setting Up the Python Environment

A "virtual environment" is an isolated container for the app's dependencies so they don't interfere with other Python software on your computer.

### Step 6.1 — Create the Virtual Environment

In the terminal inside the project folder, type the following and press Enter:

**Windows:**
```
python -m venv .venv
```

**macOS/Linux:**
```
python3 -m venv .venv
```

Wait a few seconds.  You will not see much output — that is normal.

### Step 6.2 — Activate the Virtual Environment

You must activate the environment every time you open a new terminal window.

**Windows (Command Prompt):**
```
.venv\Scripts\activate
```

**Windows (PowerShell):**
```
.venv\Scripts\Activate.ps1
```
> If you get an error about "execution policy", type this first: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**macOS/Linux:**
```
source .venv/bin/activate
```

After activation, your terminal prompt will change to show `(.venv)` at the beginning — this tells you the environment is active.

### Step 6.3 — Install the Required Packages

With the virtual environment active, type the following and press Enter:

```
pip install -r requirements.txt
```

This will download and install all the Python packages the app needs.  It may take 2–5 minutes depending on your internet connection.  You will see a lot of text scrolling — that is normal.

When it finishes, you should see a line like `Successfully installed ...`.

---

## Part 7 — Configuring the Application

The app needs to know your Azure service credentials.  These are stored in a special file called `.env` (dot env).

### Step 7.1 — Create the .env File

In the project folder, create a new file named exactly `.env` (with the dot at the beginning, no other extension).

**Windows:**
1. Open Notepad.
2. Click **File → Save As**.
3. Navigate to the `document-advisor` folder.
4. In the "File name" box, type `.env` (including the dot).
5. In "Save as type", select **"All Files (*.*)"**.
6. Click **Save**.

**macOS:**
1. Open TextEdit.
2. Click **Format → Make Plain Text**.
3. Click **File → Save**.
4. Navigate to the `document-advisor` folder.
5. Name the file `.env` and click **Save**.

### Step 7.2 — Fill in Your Credentials

Copy the template below into the `.env` file, then replace each `<placeholder>` value with the corresponding value you saved in Part 3:

```dotenv
# Azure Document Intelligence (from Step 3.1)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://YOUR-RESOURCE-NAME.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=PASTE_YOUR_KEY_1_HERE

# Azure AI Search (from Step 3.2)
AZURE_SEARCH_ENDPOINT=https://YOUR-SEARCH-NAME.search.windows.net
AZURE_SEARCH_KEY=PASTE_YOUR_ADMIN_KEY_HERE
AZURE_SEARCH_INDEX_NAME=rag-documents

# Microsoft Foundry (from Step 3.3)
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE-NAME.openai.azure.com/
AZURE_OPENAI_KEY=PASTE_YOUR_FOUNDRY_API_KEY_HERE
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2025-03-01-preview

# Azure Speech — optional, delete these lines if not using voice features
AZURE_SPEECH_KEY=PASTE_YOUR_SPEECH_KEY_HERE
AZURE_SPEECH_REGION=eastus

# Azure Translator — optional, delete these lines if not using translation
AZURE_TRANSLATOR_KEY=PASTE_YOUR_TRANSLATOR_KEY_HERE
AZURE_TRANSLATOR_REGION=global
```

> **Tips:**
> - Do not add quotes around the values.
> - Do not add spaces around the `=` sign.
> - Make sure there are no trailing spaces at the end of each line.
> - If you skipped creating the Speech or Translator services, simply delete or comment out those lines (put a `#` at the start of the line).

### Step 7.3 — Verify the .env File

Open the `.env` file in Notepad/TextEdit and double-check that:
- Every value starting with `AZURE_` is filled in with a real value (no angle brackets `<>`).
- The endpoints end with a `/` (forward slash).
- Keys are the long string of letters and numbers from the Azure Portal.

---

## Part 8 — Running the Application

### Step 8.1 — Start the App

Make sure your virtual environment is still active (you should see `(.venv)` in the terminal).  If not, repeat Step 6.2.

Type the following command and press Enter:

```
streamlit run app.py
```

### Step 8.2 — Open the App in Your Browser

After a few seconds you will see output like:

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open your web browser and go to **http://localhost:8501**

The app will load and display the chat interface.

---

## Part 9 — Using the Application (Step-by-Step Walkthrough)

### Exercise 1: Create an AI Agent in Microsoft Foundry

In this exercise you will create a simple **prompt-based agent** inside the same Foundry project you set up in Step 3.3.  The agent will use your GPT-4.1 deployment to answer questions conversationally — no code required.

#### What Is a Foundry Agent?

An agent is an AI-powered assistant hosted inside your Foundry project.  There are two types:

| Type | Description |
|------|-------------|
| **Prompt agent** | Uses a model deployment + system instructions — no custom code needed.  Great for chatbots, Q&A assistants, and guided workflows. |
| **Hosted agent** | Runs your own container with custom code (Python / C#).  Needed for advanced scenarios like tool calling, multi-step workflows, or integrations. |

In this exercise you will create a **prompt agent** so you can experience the end-to-end flow without writing any code.

#### Step 1a — Open Your Foundry Project

1. Go to **https://ai.azure.com** and sign in.  Make sure the **New Foundry** toggle is on.
2. In the upper-left corner, click the **project name** dropdown and select your project (e.g., `document-advisor-project`).

#### Step 1b — Navigate to the Agents Playground

1. In the upper-right navigation, click **"Build"**, then select **"Agents"** in the left pane.
2. You will see the **Agent setup** page (the Agents Playground).

#### Step 1c — Create a New Agent

1. Click **"+ New agent"** (or **"+ Create"**).
2. You will see a configuration panel on the right side.  Fill in the following:

   **Name:**
   ```
   document-qa-agent
   ```

   **Instructions (system prompt):** Copy and paste the following into the **Instructions** text box:
   ```
   You are a helpful document question-answering assistant.
   When a user asks a question, provide a clear, concise, and accurate answer.
   If you are unsure, say so honestly rather than guessing.
   Always be polite and professional.
   ```

   **Model deployment:** Select your **gpt-4.1** deployment from the dropdown.  (This is the deployment you created in Step 3.3d.)

3. Leave all other settings at their defaults for now.

#### Step 1d — Test the Agent in the Playground

1. On the same page you will see a **chat panel** (usually on the right or bottom).
2. Type a test message, for example:
   ```
   Hello! What can you help me with?
   ```
3. Press **Enter** (or click the send button).
4. The agent will respond using the instructions you provided.  You should see a polite, on-topic reply.
5. Try a few more questions to see how the agent behaves:
   - *"Explain quantum computing in simple terms."*
   - *"Summarise the benefits of cloud computing."*
   - *"What is retrieval-augmented generation?"*

#### Step 1e — Customise the Agent (Optional Experiments)

Try tweaking the agent to see how the behaviour changes:

- **Change the instructions** — Edit the system prompt to give the agent a different personality.  For example, add `"Always respond in bullet points."` or `"You are a pirate. Answer everything in pirate speak."` Then send a message and observe the difference.
- **Adjust the temperature** — If you see a **Temperature** slider, move it toward 0 for more deterministic answers or toward 1 for more creative responses.
- **Add knowledge (optional)** — Some Foundry projects allow you to attach files or an Azure AI Search index as a knowledge source.  If you see an **"Add data source"** or **"Knowledge"** option, try connecting the same AI Search index (`rag-documents`) you created in Step 3.2 — the agent will then answer questions grounded in your uploaded documents.

#### Step 1f — Note the Agent Details

After creating the agent, note the following for future reference:

1. **Agent name:** `document-qa-agent`
2. **Agent ID:** Shown on the agent overview page (a string like `asst_abc123...`).
3. **Project endpoint:** The same endpoint you saved in Step 3.3c.

> **Why this matters:** If you later want to call the agent programmatically (from Python or another app), you will need the project endpoint and agent name/ID.  The Foundry Python SDK (`azure-ai-projects`) lets you invoke agents from code — see the [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/agents/overview) for details.

#### Summary

In this exercise you:
- Created a prompt-based agent inside your Foundry project
- Gave it custom instructions (a system prompt)
- Tested it interactively in the Agents Playground
- Explored optional customisations like personality changes and knowledge grounding

This is the simplest way to create an agent in Foundry.  For production scenarios that require tool calling, code execution, or multi-agent orchestration, you would create a **hosted agent** using a framework like Microsoft Agent Framework — but that is beyond the scope of this introductory lab.

---

### Exercise 2: Upload Your First Document

1. On the left side of the screen, you will see the **Document Manager** panel.
2. Scroll down to "➕ Upload New Document".
3. Click **"Browse files"** and select a PDF from your computer.
   > If you do not have a PDF handy, search for a free PDF online (e.g., a product manual, a research paper abstract, or a public government report).
4. Click the **"🚀 Analyze & Index"** button.
5. Watch the progress bar:
   - **10%** — Document Intelligence is reading your PDF.
   - A preview of the first few pages will appear in an expandable box.
   - **40%** — Text is being split into chunks.
   - **55%** — The search database is being created.
   - **70%** — Vectors (embeddings) are being generated and uploaded.
   - **100%** — Done!
6. You should see a green banner: **"🎉 [Your filename] indexed successfully!"**
7. The document name appears in the **"📚 Indexed Documents"** section of the sidebar.

### Exercise 3: Ask Your First Question

1. Click in the text box at the bottom that says **"Ask a question about your documents…"**
2. Type a question about the document you uploaded and press Enter.  For example:
   - *"What is this document about?"*
   - *"What are the main topics covered?"*
   - *"Summarise the key points."*
3. Wait 3–10 seconds.  You will see a loading spinner.
4. The answer will appear, followed by a **"📚 Sources & Citations"** section.
5. Click "Sources & Citations" to expand it — you will see which pages the answer was taken from and the exact text the AI used.

### Exercise 4: Generate a Document Summary

1. Click the **"📝 Summary"** tab (next to the 💬 Chat tab, at the top of the main area).
2. Make sure your uploaded document is selected in the dropdown.
3. Click **"📝 Generate Summary"**.
4. Wait 10–30 seconds (summaries take longer because the full document is processed).
5. A structured summary with sections and page references will appear.

### Exercise 5: Change the Output Language (Optional, requires Translator key)

1. In the sidebar, find **"🌐 Output Language"**.
2. Click the dropdown and select **Hindi**, **French**, or **Telugu**.
3. Ask your next question.  The answer will be in the selected language.
4. Switch back to English at any time by selecting "English" from the dropdown.

### Exercise 6: Use Voice Input (Optional, requires Speech credentials)

1. In the Chat tab, you will see a **"🎤 Voice Input"** section with a microphone widget.
2. Click the microphone button and speak your question clearly at a normal pace.
3. Click the stop button when you are done speaking.
4. The app will display: *"🗣️ Heard: [your transcribed question]"*
5. The answer will be generated and spoken aloud automatically.

---

## Part 10 — Stopping and Restarting the App

### Stopping the App

In the terminal where the app is running, press **Ctrl + C**.  The app will stop.

### Restarting the App

1. Open a terminal in the project folder.
2. Activate the virtual environment (Step 6.2).
3. Run `streamlit run app.py`.

> **Note:** Your uploaded documents remain searchable every time you restart the app because they are stored in Azure AI Search (not locally).  However, the "Indexed Documents" list in the sidebar only shows documents uploaded in the current session.

---

## Part 11 — Common Problems and Solutions

### Problem: "⚠️ Missing Azure configuration" appears instead of the app

**Cause:** Your `.env` file is missing or has incorrect values.

**Solution:**
1. Make sure the `.env` file is in the same folder as `app.py`.
2. Open the `.env` file and verify there are no `<placeholder>` values remaining.
3. Check that you have not accidentally named the file `.env.txt` (Windows sometimes adds `.txt` without showing it).
   - In File Explorer, click View → tick "File name extensions" to see the full filename.
4. Restart the app after fixing the file.

---

### Problem: "Document Intelligence error: 401 Unauthorized"

**Cause:** The Document Intelligence key or endpoint is wrong.

**Solution:**
1. Go to the Azure Portal → your Document Intelligence resource → Keys and Endpoint.
2. Copy KEY 1 again (it is easy to accidentally copy the endpoint instead of the key).
3. Update the value in your `.env` file.
4. Restart the app.

---

### Problem: Installation of `azure-cognitiveservices-speech` fails

**Cause:** The Speech SDK requires C++ runtime components that may not be present on all systems.

**Solution:** This is an optional package.  The app works without it.
1. If you do not need voice features, delete the `azure-cognitiveservices-speech` line from `requirements.txt` and re-run `pip install -r requirements.txt`.
2. Or simply ignore the error — the speech package is the last one and all other packages will install fine.

---

### Problem: "pip is not recognised" error on Windows

**Cause:** Python was not added to PATH during installation.

**Solution:**
1. Uninstall Python from Control Panel.
2. Re-run the Python installer.
3. On the first screen, **make sure you check "Add Python to PATH"** before clicking Install.

---

### Problem: The app starts but answers are very slow

**Cause:** Expected behaviour.  GPT-4.1 typically takes 5–15 seconds to generate an answer.

**Solution:** No action needed.  The loading spinner tells you the app is working.

---

### Problem: "Could not understand the audio"

**Cause:** The audio was too quiet, too noisy, or the recording was too short.

**Solution:**
1. Make sure you are in a quiet environment.
2. Speak louder and closer to the microphone.
3. Speak a complete sentence, not just one word.
4. Ensure your microphone is not muted.

---

### Problem: Answers appear in English instead of the selected language

**Cause:** `AZURE_TRANSLATOR_KEY` is not set in `.env`.

**Solution:**
1. Complete Step 3.5 to create an Azure Translator resource.
2. Add the key and region to your `.env` file.
3. Restart the app.

---

## Part 12 — Cleaning Up Azure Resources

When you are done experimenting and want to stop any potential charges:

1. Go to the Azure Portal → **"Resource groups"**.
2. Click on `document-advisor-rg`.
3. Click **"Delete resource group"** at the top.
4. Type the resource group name to confirm, then click **"Delete"**.

This deletes ALL services created in this lab in one step.

> **Important:** This also deletes all the documents you indexed.  Re-uploading them after recreation will be necessary.

---

## Appendix A — Complete .env Template

```dotenv
# ─────────────────────────────────────────────────────────────────────────────
# RAG Document Assistant — Environment Configuration
# Copy this file to .env in the project root and fill in your Azure values.
# NEVER commit .env to version control (Git).
# ─────────────────────────────────────────────────────────────────────────────

# ── Azure Document Intelligence ───────────────────────────────────────────────
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://YOUR_RESOURCE.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=YOUR_KEY_HERE

# ── Azure AI Search ───────────────────────────────────────────────────────────
AZURE_SEARCH_ENDPOINT=https://YOUR_SEARCH_SERVICE.search.windows.net
AZURE_SEARCH_KEY=YOUR_ADMIN_KEY_HERE
AZURE_SEARCH_INDEX_NAME=rag-documents

# ── Microsoft Foundry ─────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE_NAME.openai.azure.com/
AZURE_OPENAI_KEY=YOUR_FOUNDRY_API_KEY_HERE
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2025-03-01-preview

# ── Azure Speech (optional — delete or comment out if not using) ──────────────
AZURE_SPEECH_KEY=YOUR_SPEECH_KEY_HERE
AZURE_SPEECH_REGION=eastus

# ── Azure Translator (optional — delete or comment out if not using) ──────────
AZURE_TRANSLATOR_KEY=YOUR_TRANSLATOR_KEY_HERE
AZURE_TRANSLATOR_REGION=global
```

---

## Appendix B — Quick-Start Checklist

Use this checklist to make sure you have completed every step:

- [ ] Azure account created and logged into the Portal
- [ ] Resource group `document-advisor-rg` created
- [ ] Azure Document Intelligence resource created — endpoint and key saved
- [ ] Azure AI Search resource created — URL and admin key saved
- [ ] Microsoft Foundry project created — project endpoint and API key saved
- [ ] GPT-4.1 model deployed via Foundry Model Catalog
- [ ] text-embedding-ada-002 model deployed via Foundry Model Catalog
- [ ] *(Optional)* Azure Speech resource created — key and region saved
- [ ] *(Optional)* Azure Translator resource created — key and region saved
- [ ] Python 3.10+ installed with "Add to PATH" checked
- [ ] Project folder downloaded/cloned
- [ ] Virtual environment created with `python -m venv .venv`
- [ ] Virtual environment activated (`.venv\Scripts\activate` or `source .venv/bin/activate`)
- [ ] Packages installed with `pip install -r requirements.txt`
- [ ] `.env` file created in the project root with all credentials filled in
- [ ] App launched with `streamlit run app.py`
- [ ] Browser opened to http://localhost:8501
- [ ] Test PDF uploaded successfully
- [ ] First question answered with cited sources
- [ ] *(Optional)* Foundry prompt agent created and tested in the Agents Playground

---

*End of Lab Manual*
