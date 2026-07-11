# SupportAI Database Design (02-database-design.md)

## Document Metadata
*   **Status**: Draft for Review
*   **Author**: Senior Backend Software Architect
*   **Version**: 1.0.0
*   **Date**: 2026-07-09

---

## 1. Purpose, Responsibilities, and Scope

### Purpose
This document specifies the MongoDB database layout, field mappings, index configurations, relationship structures, and query optimization rules for the SupportAI SaaS platform. It serves as the physical model standard for all repository and model layer classes.

### Responsibilities
*   Defining document structures for all 14 core system collections.
*   Enforcing standard audit and soft-delete schemas across collections.
*   Detailing relations between tables via Business UUIDs (bypassing ObjectId dependency).
*   Documenting indexing rules, including text, compound, and vector search indices.

### Scope
Covers all databases, collections, constraints, validation rules, and indexes utilized in Version 1. High-level routing or code execution specifics are delegated to subsequent documents.

---

## 2. MongoDB Selection Justification

For a production-grade multi-tenant AI RAG platform, MongoDB Atlas was chosen over traditional relational systems (PostgreSQL) or hybrid configurations (Postgres + Pinecone) for the following reasons:

1.  **Polymorphic Ingestion Schema**: Knowledge base documents, widget settings, and message payloads are semi-structured. MongoDB's dynamic schema allows documents to store arbitrary metadata tags, varying parsing outputs, and multi-channel configurations (WhatsApp, Slack) without costly table migrations.
2.  **Unified Operational & Vector Data Store**: MongoDB Atlas features native **Atlas Vector Search**. By storing text chunks and their corresponding 768-dimension vectors inside the same document, we eliminate the operational overhead, network latency, and synchronization complexities of maintaining separate databases (e.g. Postgres for metadata + Pinecone for vectors).
3.  **Horizontal Scale via Sharding**: B2B SaaS tenancy isolation aligns perfectly with MongoDB sharding. We can easily scale horizontally by sharding our collections using `company_id` as the shard key, keeping a single tenant's data isolated within specific hardware clusters.
4.  **High Write Throughput**: The analytics engine and chat messaging operations generate high volumes of log entries. MongoDB's memory-mapped storage engine (WiredTiger) handles rapid concurrent writes efficiently.

---

## 3. Core Database Design Conventions

To maintain strict architectural clean-code patterns, all collections will implement these standard conventions:

1.  **No ObjectId Exposure**: While MongoDB uses `_id` (ObjectId) as its internal primary key, all database lookups across boundaries and external APIs must use a unique index `uuid` field (e.g. `user_id`, `company_id`).
2.  **Audit Fields**: Every collection contains:
    *   `created_at`: DateTime (UTC, non-nullable)
    *   `updated_at`: DateTime (UTC, non-nullable)
    *   `created_by`: UUID (Refers to `users.user_id`, nullable only for initial signup)
    *   `updated_by`: UUID (Refers to `users.user_id`, nullable)
3.  **Soft Delete Fields**: Where soft-delete is specified:
    *   `is_deleted`: Boolean (default: `false`)
    *   `deleted_at`: DateTime (UTC, nullable, default: `null`)

---

## 4. Collection Specifications

### 1. `users` Collection
*   **Purpose**: Manages system authentication credentials, user profiles, and login flags.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "user_id": "UUID",
      "email": "String (lowercase, unique index)",
      "hashed_password": "String",
      "full_name": "String",
      "is_active": "Boolean (default: true)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID (nullable)",
      "updated_by": "UUID (nullable)"
    }
    ```
*   **Indexes**:
    *   Unique index on `user_id`
    *   Unique index on `email` (case-insensitive collation)
    *   Compound index on `(is_deleted, is_active)`
*   **Validation**: Regex check on `email` (`^[\w\.-]+@[\w\.-]+\.\w+$`).

---

### 2. `sessions` Collection
*   **Purpose**: Manages active user sessions, refresh tokens, and device identifiers.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "session_id": "UUID",
      "user_id": "UUID (Refers to users.user_id)",
      "refresh_token_hash": "String (SHA-256)",
      "ip_address": "String (nullable)",
      "user_agent": "String (nullable)",
      "expires_at": "DateTime",
      "is_revoked": "Boolean (default: false)",
      "created_at": "DateTime",
      "updated_at": "DateTime"
    }
    ```
*   **Indexes**:
    *   Unique index on `session_id`
    *   Index on `user_id`
    *   TTL index on `expires_at` (automatic cleanup of expired sessions)

---

### 3. `companies` Collection
*   **Purpose**: Stores tenant profiles, settings, and lifecycle statuses.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "company_id": "UUID",
      "name": "String",
      "slug": "String (unique, lowercase url-friendly)",
      "status": "String (ACTIVE, PENDING, SUSPENDED, ARCHIVED)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `company_id`
    *   Unique index on `slug`
    *   Index on `status`

---

### 4. `company_members` Collection
*   **Purpose**: Manages the junction between users and companies, tracking RBAC roles.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "membership_id": "UUID",
      "user_id": "UUID (Refers to users.user_id)",
      "company_id": "UUID (Refers to companies.company_id)",
      "role": "String (OWNER, ADMIN, MEMBER, VIEWER)",
      "status": "String (INVITED, ACTIVE, REMOVED)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `membership_id`
    *   Compound index on `(user_id, company_id)`
    *   Index on `(company_id, role)`

---

### 5. `knowledge` Collection
*   **Purpose**: Represents configurations, schemas, and classifications of tenant knowledge sources.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "knowledge_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "name": "String",
      "description": "String",
      "source_type": "String (MANUAL, WEB_CRAWL, FILE_UPLOAD)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `knowledge_id`
    *   Compound index on `(company_id, is_deleted)`

---

### 6. `documents` Collection
*   **Purpose**: Stores parsed text chunks and vector embeddings mapping to tenant knowledge bases.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "document_id": "UUID (Individual chunk identifier)",
      "parent_document_id": "UUID (Groups chunks of the same source file)",
      "knowledge_id": "UUID (Refers to knowledge.knowledge_id)",
      "company_id": "UUID (Refers to companies.company_id)",
      "chunk_index": "Integer",
      "content": "String (Raw text payload)",
      "vector_embedding": "Array of Floats (768 Dimensions)",
      "metadata": {
        "source_title": "String",
        "file_type": "String (PDF, TXT, MD)",
        "summary": "String",
        "tags": "Array of Strings"
      },
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `document_id`
    *   Index on `parent_document_id`
    *   Compound index on `(company_id, knowledge_id, is_deleted)`
    *   **Atlas Vector Search Index**: Configured on `vector_embedding` with Cosine Similarity metric and 768 dimensions.

---

### 7. `products` Collection
*   **Purpose**: Stores structured inventory/product metadata details for assistant context resolution.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "product_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "sku": "String",
      "name": "String",
      "description": "String",
      "price": "Double",
      "url": "String (nullable)",
      "is_available": "Boolean (default: true)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `product_id`
    *   Compound index on `(company_id, sku)`
    *   Text search index on `(name, description)` for text-query lookups.

---

### 8. `conversations` Collection
*   **Purpose**: Groups customer session logs and traces interactive communication with the AI helper.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "conversation_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "user_identifier": "String (Session/Guest cookie hash)",
      "status": "String (OPEN, RESOLVED, HANDED_OVER_TO_AGENT)",
      "last_message_at": "DateTime",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID (nullable)",
      "updated_by": "UUID (nullable)"
    }
    ```
*   **Indexes**:
    *   Unique index on `conversation_id`
    *   Compound index on `(company_id, user_identifier)`
    *   Index on `last_message_at`

---

### 9. `messages` Collection
*   **Purpose**: Stores individual conversation dialogue messages.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "message_id": "UUID",
      "conversation_id": "UUID (Refers to conversations.conversation_id)",
      "company_id": "UUID (Refers to companies.company_id)",
      "sender_type": "String (USER, ASSISTANT, HUMAN_AGENT)",
      "content": "String",
      "citations": [
        {
          "document_id": "UUID (Refers to documents.document_id)",
          "source_title": "String",
          "chunk_index": "Integer"
        }
      ],
      "feedback_score": "Integer (Enum: -1 = down, 0 = none, 1 = up)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID (nullable)",
      "updated_by": "UUID (nullable)"
    }
    ```
*   **Indexes**:
    *   Unique index on `message_id`
    *   Compound index on `(conversation_id, created_at)`
    *   Index on `(company_id, feedback_score)`

---

### 10. `widget_settings` Collection
*   **Purpose**: Configures design styles, CORS rules, and greetings for embedded support widgets.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "widget_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "theme_color": "String (Hex/HSL, default: #000000)",
      "welcome_message": "String",
      "bot_name": "String",
      "allowed_domains": "Array of Strings",
      "is_enabled": "Boolean (default: true)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `widget_id`
    *   Unique index on `company_id`

---

### 11. `ai_settings` Collection
*   **Purpose**: Preserves model execution properties (temperatures, prompt guidelines) per tenant.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "setting_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "system_prompt": "String",
      "temperature": "Double (default: 0.2)",
      "max_tokens": "Integer (default: 1024)",
      "model_name": "String (default: gemini-1.5-flash)",
      "confidence_threshold": "Double (default: 0.65)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `setting_id`
    *   Unique index on `company_id`

---

### 12. `analytics` Collection
*   **Purpose**: Log stream tracking user events for dashboard charts. Write-once, read-heavy data.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "event_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "event_type": "String (MESSAGE_SENT, HELP_HELPFUL, HELP_UNHELPFUL, AGENT_HANDOVER)",
      "event_metadata": "Document",
      "created_at": "DateTime",
      "created_by": "UUID (nullable)"
    }
    ```
*   **Indexes**:
    *   Unique index on `event_id`
    *   Compound index on `(company_id, event_type, created_at)`

---

### 13. `approvals` Collection
*   **Purpose**: Coordinates review workflow flags for uploaded content before saving vectors.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "approval_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id)",
      "entity_type": "String (KNOWLEDGE_DOCUMENT, WIDGET_THEME)",
      "entity_id": "UUID (Refers to target entity)",
      "requested_changes": "Document (Diff)",
      "status": "String (PENDING, APPROVED, REJECTED)",
      "review_notes": "String (nullable)",
      "reviewed_by": "UUID (Refers to users.user_id, nullable)",
      "reviewed_at": "DateTime (nullable)",
      "is_deleted": "Boolean (default: false)",
      "deleted_at": "DateTime (nullable)",
      "created_at": "DateTime",
      "updated_at": "DateTime",
      "created_by": "UUID",
      "updated_by": "UUID"
    }
    ```
*   **Indexes**:
    *   Unique index on `approval_id`
    *   Compound index on `(company_id, status)`

---

### 14. `audit_logs` Collection
*   **Purpose**: Immutable security registry recording administrative operations.
*   **Schema**:
    ```json
    {
      "_id": "ObjectId",
      "log_id": "UUID",
      "company_id": "UUID (Refers to companies.company_id, nullable)",
      "user_id": "UUID (Refers to users.user_id, nullable)",
      "action": "String (USER_SIGNUP, WIDGET_EDIT, USER_DELETED)",
      "ip_address": "String",
      "user_agent": "String",
      "payload_diff": "Document (nullable)",
      "created_at": "DateTime"
    }
    ```
*   **Indexes**:
    *   Unique index on `log_id`
    *   Compound index on `(company_id, created_at)`
    *   Index on `user_id`

---

## 5. Design Decisions (A/L/E)

### Decoupled Reference by UUIDs instead of ObjectIds
*   **Advantage**: High migration independence. Database collections are decoupled from MongoDB specific parameters. This allows for easily swapping parts of the store or archiving collections to S3/Snowflake without breaking database pointer relations.
*   **Limitation**: MongoDB cannot naturally enforce relational integrity natively at the query optimizer level. We must write application service layers to manage referential constraints.
*   **Future Expansion**: Easily move analytics or audit logs collections into separate databases (e.g. TimescaleDB, ClickHouse) as dataset scaling dictates.

### Embedded Chunks vs. Flat Document Structure
*   **Advantage**: Fast queries. We treat each vector chunk as a top-level document in the `documents` collection rather than an array inside a parent metadata document. This aligns directly with Atlas Vector Search's document indexing logic.
*   **Limitation**: Reconstructing the parent file layout requires a query filter on `parent_document_id`.
*   **Future Expansion**: Simple migration. A flat structure allows us to easily scale to millions of vector vectors without hitting MongoDB's 16MB document size limit.
