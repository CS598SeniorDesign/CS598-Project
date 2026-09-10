#QuestLog Frontend
The QuestLog frontend is built using **Next.js, React, and TypeScript**. This directory contains the frontend application, reusable UI components, static assets, environment configuration, and frontend Docker setup.

##Getting Started

From the 'frontend/' directory, install the project dependenices:

```bash 
npm install 
```

Start the development server:

```bash
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

#Frontend Environment Variables

A sanitized environment variable template is given at:

```text
frontend/.env.example
```

The frontend currently uses the following environment variables:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
INTERNAL_API_URL=http://backend:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```
- `NEXT_PUBLIC_API_URL` is used for browser-side communication with the Django backend.
- `INTERNAL_API_URL` can be used for communication between services inside the Docker network.
- `NEXT_PUBLIC_APP_URL` identifies the public URL of the Next.js frontend.

Real `.env` and `.env.local` files should **not** be committed to the repository.

## Docker Setup

The frontend includes its own `Dockerfile` and `.dockerignore` for containerized development.

### Build the Frontend Image

From the **project root**, run:

```bash
docker build -t questlog-frontend-test ./frontend
```

### Run the Frontend Container

Run the frontend container and expose the Next.js application on port `3000`:

```bash
docker run --rm -p 3000:3000 questlog-frontend-test
```

The application can then be accessed at:

```text
http://localhost:3000
```

Existing application routes, such as `/login`, `/signup`, etc. can be used to verify that the frontend container is running successfully.

## Docker Build Context

The frontend `.dockerignore` prevents unnecessary local and generated files from being copied into the Docker image.

Some of the excluded files and directories include:

- `node_modules`
- `.next`
- local `.env` files
- coverage output
- `.DS_Store`

This will help keeping the Docker build content smaller and preventing the local build artifacts from interfering with the container build.

## Docker Compose Integration

The frontend Docker image is designed to integrate with the team's Docker Compose environment alongside the **Django backend, PostgreSQL database, and Redis services**.

The complete Docker compose configuration is maintained at the project level. Once the full team environment is integrated, the stack can be then started from the project-level Docker compose configuration.

## Frontend Testing
Frontend uni tests use Jest and React Testing Library.
The initial unit tests cover the AvatarPicker componenet. Current tessts verify that:
1. the available avatars are rendered correctly.
2. selecting an avatar calls the onSelect handler with the corret avatar value.
Run the frontend unit tests with:

npm test

The current testing setup includes:

frontend/
├── components/ui/AvatarPicker.test.tsx
├── jest.config.ts
└── jest.setup.ts

Additional component and interaction tests can be added as frontend features are completed.

## Frontend Validation

The frontend can be checked locally using:

```bash
npm run lint
npm run typecheck
npm run build
```

Frontend unit tests can be run with:

```bash
npm test
```

During prototype 1 development, the frontend Docker image was also built and run locally tp verify that the Next.js application could successfully run inside a container.

## Frontend Project Structure

```text
```text
frontend/
├── app/                         # Next.js application routes and pages
├── components/                  # Reusable React components and component tests
├── public/                      # Static assets
├── style/                       # Additional frontend styling
├── Dockerfile                   # Frontend Docker configuration
├── .dockerignore                # Docker build exclusions
├── .env.example                 # Sanitized environment variable template
├── jest.config.ts               # Jest testing configuration
├── jest.setup.ts                # Jest test environment setup
├── package.json                 # Frontend dependencies and scripts
└── README.md                    # Frontend development documentation
```

##Development Notes
It is important to note that frontend changes should follow the team's Git workflow and be made on appropriately named feature, bug-fix, or chore branches rather than directly on main.
Also, before opening or updating a pull request, run the relevant list, typecheck, build, and test commands for the frontend changes being submitted.