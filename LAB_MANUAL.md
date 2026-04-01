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

You need to create **four Azure services**.  Follow the steps below for each one.

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

### Step 3.3 — Create Azure OpenAI

This is the AI service that generates your answers using GPT-4.1.

> **Important:** Azure OpenAI requires approval for new accounts.  If you just created your account, you may need to wait 24–48 hours for access to be granted after applying at the link below.

1. In the search bar, type **"Azure OpenAI"** and click the result.
2. If you see a message about requesting access, click the link and fill in the form.  Come back after approval.
3. Once approved, click **"+ Create"**.
4. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `document-advisor-rg`
   - **Region:** Select **"East US"** or **"East US 2"** (these have the widest model availability)
   - **Name:** Type a unique name, e.g., `openai-yourname`
   - **Pricing tier:** Standard S0
5. Click **"Review + Create"**, then **"Create"**.
6. Wait for deployment.  Click **"Go to resource"**.
7. In the left menu, click **"Keys and Endpoint"**.
8. **Copy and save:**
   - **Endpoint** (e.g., `https://openai-yourname.openai.azure.com/`)
   - **KEY 1**

#### Step 3.3a — Deploy the GPT-4.1 Model

1. On your Azure OpenAI resource page, click **"Go to Azure OpenAI Studio"** (or navigate to **https://oai.azure.com**).
2. In the left menu, click **"Deployments"**.
3. Click **"+ Create new deployment"**.
4. Fill in:
   - **Select a model:** Choose **gpt-4.1** (or gpt-4 if gpt-4.1 is not available)
   - **Deployment name:** Type exactly `gpt-4.1`
5. Click **"Create"**.

#### Step 3.3b — Deploy the Embedding Model

1. Still on the Deployments page, click **"+ Create new deployment"** again.
2. Fill in:
   - **Select a model:** Choose **text-embedding-ada-002**
   - **Deployment name:** Type exactly `text-embedding-ada-002`
3. Click **"Create"**.

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

# Azure OpenAI (from Step 3.3)
AZURE_OPENAI_ENDPOINT=https://YOUR-OPENAI-NAME.openai.azure.com/
AZURE_OPENAI_KEY=PASTE_YOUR_KEY_1_HERE
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

### Exercise 1: Upload Your First Document

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

### Exercise 2: Ask Your First Question

1. Click in the text box at the bottom that says **"Ask a question about your documents…"**
2. Type a question about the document you uploaded and press Enter.  For example:
   - *"What is this document about?"*
   - *"What are the main topics covered?"*
   - *"Summarise the key points."*
3. Wait 3–10 seconds.  You will see a loading spinner.
4. The answer will appear, followed by a **"📚 Sources & Citations"** section.
5. Click "Sources & Citations" to expand it — you will see which pages the answer was taken from and the exact text the AI used.

### Exercise 3: Generate a Document Summary

1. Click the **"📝 Summary"** tab (next to the 💬 Chat tab, at the top of the main area).
2. Make sure your uploaded document is selected in the dropdown.
3. Click **"📝 Generate Summary"**.
4. Wait 10–30 seconds (summaries take longer because the full document is processed).
5. A structured summary with sections and page references will appear.

### Exercise 4: Change the Output Language (Optional, requires Translator key)

1. In the sidebar, find **"🌐 Output Language"**.
2. Click the dropdown and select **Hindi**, **French**, or **Telugu**.
3. Ask your next question.  The answer will be in the selected language.
4. Switch back to English at any time by selecting "English" from the dropdown.

### Exercise 5: Use Voice Input (Optional, requires Speech credentials)

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

# ── Azure OpenAI ─────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=https://YOUR_OPENAI_RESOURCE.openai.azure.com/
AZURE_OPENAI_KEY=YOUR_KEY_HERE
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
- [ ] Azure OpenAI resource created — endpoint and key saved
- [ ] GPT-4.1 model deployment created in Azure OpenAI Studio
- [ ] text-embedding-ada-002 model deployment created in Azure OpenAI Studio
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

---

*End of Lab Manual*

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

# ── Azure OpenAI ─────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=https://YOUR_OPENAI_RESOURCE.openai.azure.com/
AZURE_OPENAI_KEY=YOUR_KEY_HERE
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
- [ ] Azure OpenAI resource created — endpoint and key saved
- [ ] GPT-4.1 model deployment created in Azure OpenAI Studio
- [ ] text-embedding-ada-002 model deployment created in Azure OpenAI Studio
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

---

*End of Lab Manual*
