# Recruitment-Staffing-Agent

**Recruitment-Staffing-Agent** is an automated platform for streamlining recruitment workflows. It integrates with **Google Drive**, **Google Sheets**, and **MongoDB** to process resumes, match candidates to job roles, and manage results efficiently.

---

## 🚀 Features

- **Automated Resume Processing**  
  Monitors Google Drive folders for new resume uploads and processes them in real time.

- **Role Management**  
  Reads job roles and responsibilities from the "Roles" tab of a Google Sheet and processes all resumes in the specified folder.

- **AI-Powered Matching**  
  Uses **Gemini AI** to parse and score resumes against job descriptions.

- **Result Management**  
  Writes candidate results to the "Results" tab in Google Sheets and stores them in MongoDB.

- **Duplicate Handling**  
  Keeps only the latest resume per candidate/job and removes older entries.

- **Webhook Integration**  
  Supports **Google Drive webhooks** for real-time resume processing.

- **Security**  
  Secrets and credentials are handled via environment variables and protected using `.gitignore`.

---

## ⚙️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/Recruitment-Staffing-Agent.git
cd Recruitment-Staffing-Agent
```

### 2. Create & Activate a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

- **Google Service Account JSON**  
  Download your Google Cloud service account key (`your-service-account.json`) and place it in the project root.

- **.env File**  
  Copy `.env.example` to `.env` and add your credentials:

```
GOOGLE_SERVICE_ACCOUNT_JSON=/absolute/path/to/your-service-account.json
GOOGLE_SHEET_ID=your_google_sheet_id
GEMINI_API_KEY=your_gemini_api_key
DRIVE_WEBHOOK_URL=https://your-ngrok-url/webhook/drive
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=recruitment
MONGO_COLLECTION=results
```

> 🔒 Never commit `.env` or secret JSON files to Git. They are ignored by `.gitignore`.

---

### 5. Run MongoDB Locally
```bash
mongod --dbpath ~/data/db
```

### 6. Start the FastAPI Server
```bash
uvicorn webhook.server:app --reload
```

### 7. (Optional) Expose Your Server Using ngrok
```bash
ngrok http 8000
```

---

## 📌 Usage

- **Roles Tab**:  
  Add job title, responsibilities, and folder ID in the `"Roles"` tab of your Google Sheet. The system will fetch and process all resumes from the corresponding folder.

- **Resume Upload**:  
  Upload resumes to the linked Google Drive folder. The system will automatically detect and process them.

- **Results Tab**:  
  Candidate scores and status will be written to the `"Results"` tab in your Google Sheet and saved in MongoDB.

---

## 🔐 Security

- `.env` and credential files are excluded via `.gitignore`.

### If You Accidentally Commit a Secret File:
1. **Remove** the file from your repo and Git history using:
   - [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
   - `git filter-repo`
2. **Rotate/revoke** the exposed key via your cloud provider.
3. **Force-push** the cleaned repo.

📚 See [GitHub's guide on removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) for more info.
