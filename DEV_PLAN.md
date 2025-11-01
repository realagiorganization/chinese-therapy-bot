---

# **MindWell Development Plan**

## **1. App Flow and User Scenario Design**

### **a. Main User Scenarios**

| **Priority** | **Task Description** |
| --- | --- |
| High | **Chatbot–Therapist Integration:** Define the logic connecting chatbot responses with therapist recommendations. |
| High | **Therapist Display Interface:** Determine what content is shown on the therapist profile or showcase page. |
| High | **Conversation History Management:** Design how past sessions, chat summaries, and psychological state analyses are displayed and managed. |

### **b. Chat Experience Optimization**

| **Priority** | **Task Description** |
| --- | --- |
| Medium / Long-term | **Chat Scene Design:** 1. Template-based Q&A for common mental health topics. 2. Model response quality evaluation. |
| Medium | **Model Memory:** Implement keyword-based filtering for selective conversation storage and summary generation. |

---

## **2. Cost Estimate**

### **Infrastructure (Approx. USD 162/month)**

| **Item** | **Cost** |
| --- | --- |
| Compute Resources | $100/month |
| Database & Cache | $60/month |
| Domain (.com) | $13/year and up |

### **Model Usage**

| **Stage** | **Input** | **Output** | **Unit** |
| --- | --- | --- | --- |
| Testing Phase | $0.5 | $1.5 | per 1M tokens |
| Production Phase | $3 | $15 | per 1M tokens |
| **Estimated input-output ratio:** 1:2 |  |  |  |

### **AI Coding Tools**

- Claude Code Mirror: ¥162/month

---

## **3. Development Timeline (Rankang)**

| **Week** | **Milestone** | **Details** |
| --- | --- | --- |
| Weeks 1–4 | **Core Scene Development** | - Model Integration - Account Management (SMS login, Google/third-party login) - Therapist Data Management - Frontend prototype for early testing |
| Weeks 5–7 | **iOS Development & App Store Release** |  |
| Weeks 8–12 | **Model Refinement** | - Add RAG filtering and query context - Implement model memory system |

---

## **4. Development Log**

### **Business Logic & Backend**

#### **Account Management**

- Username/password login ✅ *(deprecated before launch)*
- SMS login (planned)
- Third-party account integration (Google, etc.)
- Token renewal ✅

#### **Chat System**

- Persistent conversation storage
  - Real-time chat logging ✅ *(message-level S3 persistence via ChatTranscriptStorage)*
  - Daily chat snapshot storage ✅ *(persisted to S3 via ChatTranscriptStorage)*
- Summary generation
  - Daily summaries ✅ *(pipeline implemented via Summary Scheduler Agent)*
  - Weekly summaries ✅ *(weekly aggregation + storage complete)*
- Guided chat templates for common scenes ✅ *(curated dataset `chat_templates.json`, `/api/chat/templates`, and web quick-start chips).*

#### **Model Integration**

- Static model response ✅ *(deprecated before launch)*
- Debug-stage raw model integration *(tentatively AWS Bedrock)*
- Intelligent agent integration

#### **Therapist Data**

- list/get API ✅
- Script for scraping therapist data and injecting into database ✅ *(Data Sync agent `mindwell-data-sync` publishes normalized profiles to `S3_BUCKET_THERAPISTS`.)*
- Internationalization (i18n) of therapist information ✅

#### **AWS Integration**

- RDS
- EC2 instances

---

## **5. Intelligent Agent Functionality**

### **Core Modules**

- **Daily Conversation Summary**
  - Title
  - Overview
  - “Spotlight”: one-line highlight or distilled insight
- **Weekly Summary**
  - Generate cumulative summaries
- **Full Conversation History**
  - Create global prompt context
  - Extract recurring discussion topics

### **Therapist Recommendation**

- Context injection and prompt standardization
- Prompt evaluation
- Text vectorization and semantic retrieval

---

## **6. Mobile Application**

### **Login & Authentication**

- Account-based login ✅ *(deprecated later)*
- SMS login
- Third-party account integration
- Token renewal

### **Chat Functionality**

- Streamed response integration ✅
- Offline transcript caching ✅ *(AsyncStorage-backed restore in the Expo client.)*
- Push notification scaffolding ✅ *(Expo Notifications registration with device token caching.)*
- **Input Methods:**
  - Text input
  - Voice input via local system model (iOS ✅ / Android pending)
  - WeChat-style “hold to speak” voice input ✅
  - Auto language detection ✅ *(LanguageDetector service auto-resolves locale -> shared across web/mobile states.)*
  - Server-side ASR (speech recognition)
- **Output (Voice Playback):**
  - RN-TTS integration ✅
  - Sentence-level segmentation ✅
  - Adjustable voice rate and tone
  - Option to disable voice playback in Settings
  - Interrupt voice output upon new input trigger

### **Therapist Interface**

- Therapist overview ✅
- Therapist detail page ✅
- Therapist filtering functionality (planned)

### **Explore Page**

- Explore modules for breathing exercises, psychoeducation resources, and trending themes delivered via feature flags and personalized data pipelines. (✅ prototype shipped)

### **Journey Page**

- **Weekly Reports (Past 10 Weeks)**
- **Daily Reports (Past 10 Days)**
  - Title + Spotlight (clickable to detail page)
  - Detail View:
    - **Tab 1:** Date, Title, Spotlight, Summary
    - **Tab 2:** Chat Records

### **Localization**

- Chinese interface support (i18n)

### **Platform Adaptation**

- iOS optimization
- Android optimization

---

## **7. Deployment & Operations**

### **Bug Tracker**

| **Issue** | **Description** | **Status** |
| --- | --- | --- |
| /therapy/chat/stream triggers “access denied” | Does not affect pre-request validation but returns error post-request | Unresolved |

---

## **8. Additional Notes**

- Integration with Google and other third-party account management platforms in progress.

---

Would you like me to also convert this into a **formatted technical document template (e.g., Markdown → PDF or DOCX)** with consistent section numbering, table of contents, and company footer branding (e.g., “MindWell Confidential – 2025”)? That would make it suitable for investor decks or engineering sprints.
