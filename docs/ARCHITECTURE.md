# QuestLog Architecture & UML Diagrams

Visual reference for how QuestLog is built and how its pieces talk to each other. All diagrams are written in
[Mermaid](https://mermaid.js.org/), so GitHub renders them directly and they can be edited as text in the same PR as
the code they describe.

> **Keeping this current:** when a PR adds a model, endpoint, container or CI job, update the matching diagram in the
> same PR. To preview locally, use the VS Code *Markdown Preview Mermaid Support* extension or paste a block into
> <https://mermaid.live>.

## Contents

1. [System Context](#1-system-context)
2. [Container Runtime (Docker Compose)](#2-container-runtime-docker-compose)
3. [Backend Module Structure](#3-backend-module-structure)
4. [UML Class Diagram — Domain Models](#4-uml-class-diagram--domain-models)
5. [UML Class Diagram — API, Permissions & Services](#5-uml-class-diagram--api-permissions--services)
6. [Entity Relationship Diagrams](#6-entity-relationship-diagrams)
7. [Request & Authorization Pipeline](#7-request--authorization-pipeline)
8. [Sequence — Sign Up, Verify Email & Log In](#8-sequence--sign-up-verify-email--log-in)
9. [Sequence — Game Lookup with BGG Fallback](#9-sequence--game-lookup-with-bgg-fallback)
10. [Sequence — Library Add & Soft Delete](#10-sequence--library-add--soft-delete)
11. [Activity — Recommendation Engine](#11-activity--recommendation-engine)
12. [CI/CD Pipeline](#12-cicd-pipeline)

---

## 1. System Context

The browser only ever talks to the Next.js server. Next.js serves the pages and proxies `/_allauth/*` (authentication)
and `/api/*` (REST API) to Django, so the session and CSRF cookies are same-origin and no CORS is needed.

```mermaid
flowchart LR
    user(["👤 Player<br/>(web browser)"])

    subgraph questlog["QuestLog"]
        direction LR
        next["<b>Next.js 16 frontend</b><br/>React 19 · TypeScript · Tailwind<br/>:3000"]
        django["<b>Django 6 backend</b><br/>DRF · django-allauth headless<br/>:8000"]
        pg[("<b>PostgreSQL 17</b><br/>application data")]
        redis[("<b>Redis</b><br/>cache · sessions · rate limits")]
    end

    bgg["<b>BoardGameGeek</b><br/>XML API2 (HTTPS)"]
    smtp["SMTP server<br/>(console backend in dev)"]

    user -- "HTTPS pages" --> next
    next -- "rewrite /_allauth/* · /api/*" --> django
    django -- "ORM" --> pg
    django -- "django-redis" --> redis
    django -- "game details · play history<br/>(parsed with defusedxml)" --> bgg
    django -- "verification &<br/>password reset email" --> smtp
```

| Redis DB | Purpose |
| :---: | :--- |
| `0` | Default cache: recommendation results, DRF throttle counters, allauth rate limits, readiness probe |
| `1` | Session cache (`cached_db` engine — sessions are also persisted in Postgres) |
| `2` | Reserved for a Celery broker (no worker yet) |

---

## 2. Container Runtime (Docker Compose)

`docker compose up` starts four containers on the `questlog-net` bridge network. Health checks gate start-up order so
the backend never starts before its dependencies are ready, and the frontend never starts before the backend.

```mermaid
flowchart TB
    dev(["Developer machine"])

    subgraph net["Docker network: questlog-net"]
        direction TB
        fe["<b>questlog-nextjs</b><br/>target: dev · next dev<br/>env: ./frontend/.env"]
        be["<b>questlog-django</b><br/>target: dev · runserver<br/>entrypoint: wait for DB → migrate<br/>env: ./.env"]
        db[("<b>questlog-db</b><br/>postgres:17")]
        rd[("<b>questlog-redis</b><br/>redis · requirepass · AOF")]
    end

    vpg[/"volume: postgres_data"/]
    vrd[/"volume: redis_data"/]
    vsrc[/"bind mounts: ./backend · ./frontend<br/>volumes: backend_venv · frontend_node_modules · frontend_next"/]

    dev -- ":3000" --> fe
    dev -- ":8000" --> be
    dev -. ":5432 / :6379<br/>(dev only)" .-> db & rd

    fe -- "depends_on: backend healthy<br/>(GET /health/)" --> be
    be -- "depends_on: healthy<br/>(pg_isready)" --> db
    be -- "depends_on: healthy<br/>(redis-cli ping)" --> rd

    db --- vpg
    rd --- vrd
    fe & be --- vsrc
```

Production images use the `production` Dockerfile targets: gunicorn as the unprivileged `appuser` for Django, and the
Next.js standalone server as `nextjs`.

---

## 3. Backend Module Structure

Each Django app owns its models and endpoints. `core` holds the cross-cutting pieces (permissions, mixins, throttles,
feature flags, health probes) so the feature apps never depend on each other's views.

```mermaid
flowchart TB
    config["<b>config</b><br/>settings · root URLs · WSGI/ASGI"]

    subgraph features["Feature apps"]
        direction LR
        users["<b>users</b><br/>User · roles (Groups)<br/>RoleAssignmentLog"]
        profiles["<b>profiles</b><br/>Profile · GameGroup<br/>PlayerTag"]
        catalog["<b>catalog</b><br/>BoardGame + BGG metadata<br/>/api/v1/games/"]
        tracking["<b>tracking</b><br/>LibraryItem · Rating<br/>PlaySession · SessionPlayer<br/>/api/v1/library/"]
        recs["<b>recommendations</b><br/>strategies · content model<br/>/api/v1/recommendations/"]
    end

    core["<b>core</b><br/>permissions · mixins · throttles<br/>feature_flags · health views<br/>seed command · XML utils"]
    allauth["<b>django-allauth</b><br/>account · headless · mfa"]

    config --> features
    config --> core
    config --> allauth

    profiles --> users
    tracking --> catalog
    tracking --> profiles
    recs --> catalog
    recs --> tracking
    catalog --> core
    tracking --> core
    recs --> core
    users -. "AUTH_USER_MODEL" .-> allauth
```

Arrows point from a module to the module it imports.

---

## 4. UML Class Diagram — Domain Models

Persistent model classes, their key fields and behavior. `BGGAttribute` is an abstract base class (no table); its six
subclasses share its fields and `__str__`.

```mermaid
classDiagram
    direction LR

    class AbstractUser {
        <<Django>>
    }
    class User {
        +UUID id
        +str email
        +datetime deleted_at
        +has_role(*names) bool
        +is_moderator() bool
        +is_admin_role() bool
    }
    class UserManager {
        +create_user(email, password) User
        +create_superuser(email, password) User
    }
    class RoleAssignmentLog {
        +str role
        +datetime assigned_at
    }
    AbstractUser <|-- User
    UserManager ..> User : creates
    User "1" --> "*" RoleAssignmentLog : role_history

    class Profile {
        +str display_name
        +str bio
        +str privacy_level
        +str bgg_username
    }
    class GameGroup {
        +str name
        +str description
    }
    class PlayerTag {
        +str tag_type
    }
    User "1" -- "0..1" Profile
    Profile "*" -- "*" Profile : friends
    User "*" -- "*" GameGroup : members
    User "1" --> "*" PlayerTag : tags_given / tags_received

    class BGGAttribute {
        <<abstract>>
        +int bgg_id
        +str name
    }
    class Category
    class Mechanic
    class Publisher
    class Designer
    class Artist
    class Family
    BGGAttribute <|-- Category
    BGGAttribute <|-- Mechanic
    BGGAttribute <|-- Publisher
    BGGAttribute <|-- Designer
    BGGAttribute <|-- Artist
    BGGAttribute <|-- Family

    class BoardGame {
        +int bgg_id
        +str primary_name
        +int year_published
        +int minimum_players
        +int maximum_players
        +int playing_time
        +Decimal average_rating
        +Decimal average_weight
        +int bgg_rank
        +create_from_xml(xml_item, backup_name)$ BoardGame
        -_handle_links(instance, xml_item)$
    }
    BoardGame "*" -- "*" BGGAttribute : categories, mechanics, publishers, designers, artists, families

    class LibraryItem {
        +str ownership
        +bool is_played
        +str house_rules
        +datetime added_at
        +datetime deleted_at
        +add_for_user(user, game)$ LibraryItem
        +soft_delete()
    }
    class LibraryItemQuerySet {
        +active() LibraryItemQuerySet
        +owned() LibraryItemQuerySet
        +wishlisted() LibraryItemQuerySet
    }
    class ActiveLibraryItemManager {
        +get_queryset() LibraryItemQuerySet
    }
    class Rating {
        +float experience
        +float mechanics
        +float replayability
        +float enjoyment
    }
    class PlaySession {
        +int bgg_play_id
        +date play_date
        +int play_time_minutes
        +int quantity
        +bool is_incomplete
        +str location
        +create_from_xml(xml_item, user, bgg_username)$ PlaySession
    }
    class SessionPlayer {
        +str guest_name
        +float score
        +bool is_winner
    }
    ActiveLibraryItemManager ..> LibraryItemQuerySet : returns active()
    LibraryItem ..> ActiveLibraryItemManager : objects
    User "1" --> "*" LibraryItem
    BoardGame "1" --> "*" LibraryItem
    User "1" --> "*" Rating
    BoardGame "1" --> "*" Rating
    BoardGame "1" --> "*" PlaySession
    GameGroup "0..1" --> "*" PlaySession
    PlaySession "1" *-- "*" SessionPlayer : players
    User "0..1" --> "*" SessionPlayer : registered player

    class RecommendationProfile {
        +bool use_personal_data
        +int preferred_player_count
        +int preferred_max_play_time
        +Decimal preferred_complexity
        +for_user(user)$ RecommendationProfile
    }
    class RecommendationFeedback {
        +str sentiment
        +str strategy
    }
    User "1" -- "0..1" RecommendationProfile
    RecommendationProfile "*" -- "*" Category : preferred_categories
    RecommendationProfile "*" -- "*" Mechanic : preferred_mechanics
    User "1" --> "*" RecommendationFeedback
    BoardGame "1" --> "*" RecommendationFeedback
```

---

## 5. UML Class Diagram — API, Permissions & Services

How the REST layer is composed. Views stay thin: they combine reusable permission classes and mixins from `core` and
delegate work to model methods or service classes.

```mermaid
classDiagram
    direction TB

    class BasePermission {
        <<DRF>>
        +has_permission(request, view) bool
        +has_object_permission(request, view, obj) bool
    }
    class IsOwnerOrModerator {
        +has_permission() bool
        +has_object_permission() bool
    }
    class IsModeratorOrAdmin
    class IsAdminRole
    class FeatureFlagPermission {
        +has_permission() bool
    }
    BasePermission <|-- IsOwnerOrModerator
    BasePermission <|-- IsModeratorOrAdmin
    BasePermission <|-- IsAdminRole
    BasePermission <|-- FeatureFlagPermission

    class OwnedQuerysetMixin {
        +str owner_field
        +bool moderators_see_all
        +get_queryset() QuerySet
    }
    class ScopedRateThrottle {
        <<DRF>>
    }
    class BggSyncRateThrottle {
        scope = "bgg-sync"
    }
    class RecommendationRateThrottle {
        scope = "recommendations"
    }
    ScopedRateThrottle <|-- BggSyncRateThrottle
    ScopedRateThrottle <|-- RecommendationRateThrottle

    class BoardGameViewSet {
        list · retrieve
        +retrieve() Response
    }
    class LibraryItemViewSet {
        list · create · retrieve · update · destroy
        +create() Response
        +perform_destroy(instance)
    }
    class RecommendationListView {
        +get() Response
    }
    class RecommendationProfileView {
        +get_object() RecommendationProfile
    }
    class RecommendationFeedbackViewSet {
        +create() Response
    }
    class HealthCheckView {
        +get() Response
    }
    class ReadinessCheckView {
        +get() Response
    }

    OwnedQuerysetMixin <|-- LibraryItemViewSet
    LibraryItemViewSet ..> IsOwnerOrModerator : permission
    RecommendationFeedbackViewSet ..> IsOwnerOrModerator : permission
    RecommendationListView ..> RecommendationRateThrottle : throttle

    class RecommendationService {
        +User user
        +recommend(strategy, limit, **params) RecommendationResult
        -_compute() RecommendationResult
        -_basic_fallback() RecommendationResult
        -_run() tuple
        -_cache_key() str
    }
    class RecommendationContext {
        +ensure_consent()
        +interactions() DataFrame
        +content_model() ContentModel
        +personal_scores() Series
    }
    class StrategySpec {
        +handler
        +bool requires_personal_data
        +bool fallback_when_empty
    }
    class ContentModel {
        +taste_from_games(weights) Taste
        +taste_from_preferences() Taste
        +scores(taste) Series
        +most_similar(game_id, candidates) tuple
    }
    class Taste {
        +is_empty() bool
        +blend(other, weight) Taste
    }
    class RecommendationResult
    RecommendationListView ..> RecommendationService : uses
    RecommendationService ..> StrategySpec : looks up STRATEGIES
    RecommendationService ..> RecommendationContext : builds
    RecommendationService ..> RecommendationResult : returns
    RecommendationContext ..> ContentModel
    ContentModel ..> Taste
```

---

## 6. Entity Relationship Diagrams

Database-level view (one box per table). Django adds a join table for each many-to-many relationship, shown here as
`}o--o{`.

### 6a. Accounts, roles & social

```mermaid
erDiagram
    USER {
        uuid id PK
        varchar email UK
        varchar password "Argon2 hash"
        bool is_active
        bool is_staff
        datetime date_joined
        datetime deleted_at "soft delete, indexed"
    }
    AUTH_GROUP {
        int id PK
        varchar name UK "user, moderator, admin"
    }
    ROLE_ASSIGNMENT_LOG {
        int id PK
        uuid user_id FK
        uuid assigned_by_id FK "SET NULL"
        varchar role
        datetime assigned_at
    }
    ACCOUNT_EMAILADDRESS {
        int id PK
        uuid user_id FK
        varchar email
        bool verified
        bool primary
    }
    MFA_AUTHENTICATOR {
        int id PK
        uuid user_id FK
        varchar type "totp, recovery_codes, webauthn"
    }
    PROFILE {
        int id PK
        uuid user_id FK "one-to-one"
        varchar display_name
        text bio
        varchar privacy_level "PUBLIC, FRIENDS, PRIVATE"
        varchar bgg_username "unique when set, case-insensitive"
    }
    GAME_GROUP {
        int id PK
        uuid created_by_id FK "SET NULL"
        varchar name
        text description
    }
    PLAYER_TAG {
        int id PK
        uuid assigning_user_id FK
        uuid target_user_id FK
        varchar tag_type "MORTAL_ENEMY, SIDEKICK"
    }

    USER }o--o{ AUTH_GROUP : "has role"
    USER ||--o{ ROLE_ASSIGNMENT_LOG : "role history"
    USER ||--o{ ACCOUNT_EMAILADDRESS : "verifies"
    USER ||--o{ MFA_AUTHENTICATOR : "secures"
    USER ||--o| PROFILE : "has"
    PROFILE }o--o{ PROFILE : "friends"
    USER ||--o{ GAME_GROUP : "created"
    USER }o--o{ GAME_GROUP : "member of"
    USER ||--o{ PLAYER_TAG : "assigns"
    USER ||--o{ PLAYER_TAG : "is tagged"
```

`ACCOUNT_EMAILADDRESS` and `MFA_AUTHENTICATOR` are owned by django-allauth; they are shown because the sign-up and MFA
flows depend on them.

### 6b. Catalog, tracking & recommendations

```mermaid
erDiagram
    USER {
        uuid id PK
    }
    BOARD_GAME {
        int bgg_id PK "BoardGameGeek ID"
        varchar primary_name
        int year_published
        int minimum_players
        int maximum_players
        int playing_time
        decimal average_rating
        decimal average_weight
        int bgg_rank
    }
    BGG_ATTRIBUTE {
        int bgg_id PK
        varchar name "one table each: category, mechanic, publisher, designer, artist, family"
    }
    LIBRARY_ITEM {
        int id PK
        uuid user_id FK
        int game_id FK
        varchar ownership "OWNED, WISHLISTED"
        bool is_played
        text house_rules
        datetime added_at
        datetime deleted_at "soft delete; unique active row per user+game"
    }
    RATING {
        int id PK
        uuid user_id FK
        int game_id FK "unique with user"
        float experience
        float mechanics
        float replayability
        float enjoyment
    }
    GAME_GROUP {
        int id PK
    }
    PLAY_SESSION {
        int id PK
        int game_id FK
        int group_id FK "nullable"
        uuid created_by_id FK "SET NULL"
        bigint bgg_play_id UK "set for BGG imports"
        date play_date "indexed"
        int play_time_minutes
        int quantity "at least 1"
        bool is_incomplete
        varchar location
        text notes
    }
    SESSION_PLAYER {
        int id PK
        int session_id FK
        uuid user_id FK "registered player, or"
        varchar guest_name "guest; exactly one is set"
        float score
        bool is_winner
    }
    RECOMMENDATION_PROFILE {
        int id PK
        uuid user_id FK "one-to-one"
        bool use_personal_data "consent, default false"
        smallint preferred_player_count
        int preferred_max_play_time
        decimal preferred_complexity
    }
    RECOMMENDATION_FEEDBACK {
        int id PK
        uuid user_id FK
        int game_id FK "unique with user"
        varchar sentiment "LIKE, DISLIKE"
        varchar strategy
    }

    BOARD_GAME }o--o{ BGG_ATTRIBUTE : "tagged with"
    USER ||--o{ LIBRARY_ITEM : "collects"
    BOARD_GAME ||--o{ LIBRARY_ITEM : "appears in"
    USER ||--o{ RATING : "rates"
    BOARD_GAME ||--o{ RATING : "rated in"
    BOARD_GAME ||--o{ PLAY_SESSION : "played in"
    GAME_GROUP |o--o{ PLAY_SESSION : "hosts"
    USER |o--o{ PLAY_SESSION : "logged"
    PLAY_SESSION ||--|{ SESSION_PLAYER : "players"
    USER |o--o{ SESSION_PLAYER : "plays as"
    USER ||--o| RECOMMENDATION_PROFILE : "configures"
    RECOMMENDATION_PROFILE }o--o{ BGG_ATTRIBUTE : "prefers (categories, mechanics)"
    USER ||--o{ RECOMMENDATION_FEEDBACK : "reacts"
    BOARD_GAME ||--o{ RECOMMENDATION_FEEDBACK : "receives"
```

---

## 7. Request & Authorization Pipeline

Every API request passes through the same layers. Each layer can stop the request early with the status shown.

```mermaid
flowchart TD
    req(["Browser request<br/>/api/v1/... or /_allauth/..."]) --> next["Next.js rewrite<br/>adds security headers to pages"]
    next --> mw["Django middleware<br/>SecurityMiddleware · Session · CSRF ·<br/>Authentication · allauth AccountMiddleware"]
    mw --> auth["DRF SessionAuthentication<br/>(CSRF enforced on POST/PUT/PATCH/DELETE)"]
    auth --> ff{"FeatureFlagPermission<br/>(when the view sets feature_flag)"}
    ff -- "flag off" --> e404(["404 Not Found"])
    ff -- "flag on / not flagged" --> perm{"View permissions<br/>IsAuthenticated · IsOwnerOrModerator ·<br/>IsModeratorOrAdmin · IsAdminRole"}
    perm -- "anonymous" --> e401(["401/403"])
    perm -- "wrong role" --> e403(["403 Forbidden"])
    perm -- "allowed" --> thr{"Throttles (Redis)<br/>anon 60/min · user 300/min ·<br/>recommendations 60/min · bgg-sync 3/min"}
    thr -- "over limit" --> e429(["429 Too Many Requests"])
    thr -- "ok" --> qs["OwnedQuerysetMixin<br/>non-moderators only see their own rows"]
    qs --> obj{"has_object_permission<br/>(retrieve/update/delete)"}
    obj -- "not owner" --> e404b(["404 (row filtered out)"])
    obj -- "owner or moderator" --> view["ViewSet → model method / service → ORM"]
    view --> resp(["2xx JSON response"])
```

---

## 8. Sequence — Sign Up, Verify Email & Log In

Authentication uses django-allauth's headless *browser* client: an HttpOnly session cookie plus a CSRF token, never a
token stored in JavaScript.

```mermaid
sequenceDiagram
    autonumber
    actor P as Player
    participant FE as Next.js page
    participant AA as Django · allauth headless
    participant DB as PostgreSQL
    participant M as Mail backend

    P->>FE: Open /signup, submit email + password
    FE->>AA: GET /_allauth/browser/v1/auth/session
    AA-->>FE: 401 + Set-Cookie csrf_token
    FE->>AA: POST /auth/signup (X-CSRFToken)
    AA->>AA: Validate password (similarity, length, common, numeric)
    AA->>DB: INSERT user (Argon2 hash), email address (unverified)
    Note over AA,DB: post_save signal adds the user to the "user" group
    AA->>M: Send verification link (/account/verify-email/{key})
    AA-->>FE: 401 pending flow: verify_email
    P->>FE: Click link in email
    FE->>AA: POST /auth/email/verify {key}
    AA->>DB: Mark email verified
    AA-->>FE: 200, or 401 when a login is still required
    FE-->>P: "Email verified" → continue to /login?setup=mfa

    P->>FE: Submit credentials on /login
    FE->>AA: GET /auth/session → csrf_token
    FE->>AA: POST /auth/login (X-CSRFToken)
    alt Account has MFA enabled
        AA-->>FE: 401 pending flow: mfa_authenticate
        FE-->>P: "Another verification step is required"
        Note over FE,AA: Backend supports TOTP, recovery codes and passkeys,<br/>but the login page does not call /auth/2fa/authenticate yet
    else No MFA
        AA-->>FE: 200 is_authenticated (HttpOnly session cookie, SameSite=Lax)
        alt Arrived with ?setup=mfa
            FE-->>P: /mfa-setup (behind FEATURE_MFA_SETUP)
            P->>FE: Scan QR code, enter TOTP code
            FE->>AA: POST /auth/reauthenticate, then POST /account/authenticators/totp
            AA->>DB: Store TOTP authenticator + recovery codes
        else Normal login
            FE-->>P: /avatar-selection → dashboard
        end
    end
```

---

## 9. Sequence — Game Lookup with BGG Fallback

The catalog is a local cache of BoardGameGeek. A game is fetched from BGG the first time anyone looks it up.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant V as BoardGameViewSet
    participant U as catalog.utils
    participant DB as PostgreSQL
    participant BGG as BGG XML API2

    C->>V: GET /api/v1/games/{bgg_id}/
    V->>U: get_existing_board_game(bgg_id)
    U->>DB: SELECT board game by bgg_id
    alt Cached locally
        DB-->>U: BoardGame
    else Not cached
        U->>BGG: GET /xmlapi2/thing?id={bgg_id}&stats=1 (10 s timeout)
        alt BGG responds with an item
            BGG-->>U: XML
            U->>U: Parse with defusedxml
            U->>DB: BoardGame.create_from_xml → upsert game + link categories, mechanics, ...
        else Timeout, HTTP error or bad XML
            U->>U: Log warning
            U->>DB: Create placeholder record ("Unknown")
        end
    end
    U-->>V: BoardGame
    V-->>C: 200 BoardGameDetailSerializer JSON
```

---

## 10. Sequence — Library Add & Soft Delete

Removing a game from a library sets `deleted_at` instead of deleting the row, so the data can be restored or audited.
Re-adding a removed game reuses the same row.

```mermaid
sequenceDiagram
    autonumber
    actor P as Player
    participant V as LibraryItemViewSet
    participant L as LibraryItem
    participant DB as PostgreSQL
    participant S as Recommendation signals
    participant R as Redis cache

    P->>V: POST /api/v1/library/ {game, ownership}
    V->>V: IsAuthenticated + IsOwnerOrModerator
    V->>L: add_for_user(user, game, ...)
    alt Active item already exists
        L-->>V: LibraryItemAlreadyExistsError
        V-->>P: 409 Conflict
    else New, or previously soft-deleted
        L->>DB: INSERT, or restore row (deleted_at = NULL)
        DB-->>S: post_save
        S->>R: Bump the user's recommendation cache version
        V-->>P: 201 Created
    end

    P->>V: DELETE /api/v1/library/{id}/
    V->>V: OwnedQuerysetMixin hides other users' rows (404)
    V->>L: perform_destroy → soft_delete()
    L->>DB: UPDATE deleted_at = now()
    DB-->>S: post_save
    S->>R: Invalidate cached recommendations
    V-->>P: 204 No Content
    Note over L,DB: The default manager only returns active rows,<br/>so the item disappears from every list.
```

---

## 11. Activity — Recommendation Engine

`RecommendationService` answers from cache when possible, enforces consent before reading personal data, and falls back
to basic strategies that use catalog-wide data only.

```mermaid
flowchart TD
    start(["GET /api/v1/recommendations/?strategy=..."]) --> thr{"Throttle<br/>60/min per user"}
    thr -- "over limit" --> t429(["429"])
    thr -- "ok" --> cache{"Cached result for<br/>user + version + strategy + params?"}
    cache -- "hit" --> done(["200 recommendations"])
    cache -- "miss" --> spec["Look up StrategySpec"]
    spec --> consent{"Strategy needs personal data<br/>and user has not opted in?"}
    consent -- "yes" --> fallback["Basic fallback: popular → top rated<br/>reason: opt_in_required"]
    consent -- "no" --> run["Run strategy handler<br/>(content model · plays · ratings · library)"]
    run --> filter["Drop games the user disliked"]
    filter --> empty{"No results and<br/>fallback_when_empty?"}
    empty -- "yes" --> fallback2["Basic fallback<br/>reason: not_enough_data"]
    empty -- "no" --> store["Cache result for 10 minutes"]
    fallback --> store
    fallback2 --> store
    store --> done

    change(["LibraryItem · Rating · SessionPlayer ·<br/>RecommendationFeedback · RecommendationProfile<br/>saved or deleted"]) -. "signal" .-> inv["Bump user's cache version<br/>(old results ignored)"]
    inv -.-> cache
```

| Basic (no personal data) | Personal (requires `use_personal_data`) |
| :--- | :--- |
| `popular`, `top_rated`, `decision_chart` | `for_you`, `similar_to_recent`, `not_played_recently`, `unplayed_library`, `unplayed_wishlist`, `most_wins`, `redemption_arc` |

---

## 12. CI/CD Pipeline

GitHub Actions runs on every push to a working branch and on every pull request into `main`, `testing`, `qa` and
`production`. Jobs run in parallel; the report and summary jobs wait for the others.

```mermaid
flowchart LR
    trigger(["push: feature/** · bugfix/** · chore/** ...<br/>pull_request → main · testing · qa · production"])

    subgraph always["Every run"]
        direction TB
        bl["Backend lint<br/>Ruff · complexipy ≤10 · mypy ·<br/>migration drift + lintmigrations"]
        fl["Frontend lint<br/>ESLint + SonarJS ≤10 · tsc · Prettier"]
        ss["Secret scan<br/>TruffleHog"]
        bt["Backend unit tests<br/>pytest · Postgres + Redis services ·<br/>coverage ≥ 60%"]
        ft["Frontend unit tests<br/>Jest + coverage"]
        dc["Docker Compose smoke test<br/>build · up · /health/ · /ready/ ·<br/>migrate --check"]
    end

    subgraph pr["Pull requests only"]
        direction TB
        dr["Dependency review<br/>blocks new moderate+ CVEs"]
        da["Dependency audit<br/>uv audit · npm audit (runtime + root)"]
    end

    subgraph gated["Branch-gated"]
        direction TB
        qa["QA validation<br/>testing / qa branches"]
        prod["Production gate<br/>production branch"]
    end

    report["Document CI validation<br/>posts results + coverage to<br/>issues linked by Closes #N"]
    summary["CI summary<br/>GitHub step summary"]

    trigger --> always & pr & gated
    bl & fl & ss & bt & ft & dc --> report
    bt & ft & qa --> prod
    always & pr & gated & report --> summary
```

Release flow: feature branch → PR (one approval, all checks green) → `main` → annotated tag (`v0.1.0-alpha`,
`v0.5.0-alpha`, ...).
