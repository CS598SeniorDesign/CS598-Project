## Frontend Docker Setup

The Questlog frontend is a Next.js application located in the `frontend/` directory.

### Build the frontend image

From the project root, build the frontend Docker image with:

```bash
docker build -t questlog-frontend-test ./frontend
```

### Run the frontend container

Run the container and expose the Next.js application on port 3000:

```bash
docker run --rm -p 3000:3000 questlog-frontend-test
```

The frontend can then be accessed at:

```text
http://localhost:3000
```

### Frontend environment variables

Frontend environment variables are documented in:

```text
frontend/.env.example
```

Copy the example file when configuring a local frontend environment. Do not commit real environment files or secrets.

The frontend Docker image is designed to integrate with the project's Docker Compose environment so that the frontend can run alongside the backend and database services.
