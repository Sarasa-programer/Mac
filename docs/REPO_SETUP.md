# Repository Setup and Versioning Guide

## Repository Information
- **Remote URL**: `https://github.com/Sarasa-programer/Mac.git`
- **Current Version**: 1.1 (Branch: `version-1.1`)

## Versioning Scheme
This project follows a branching strategy where major independent versions are maintained in separate branches.

- **`main` / `master`**: Stable production code.
- **`version-1.1`**: The current active development branch for the "Multi-Provider Architecture" release.
    - Features: OpenRouter (Qwen), OpenAI (Whisper), Local Inference.
    - Status: Beta / Release Candidate.
- **`independent`**: Legacy or previous experimental branch.

## Setup Instructions

### 1. Cloning the Repository
```bash
git clone https://github.com/Sarasa-programer/Mac.git
cd Mac
git checkout version-1.1
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and populate keys:
```bash
cp .env.example .env
# Edit .env
```
Required keys for v1.1:
- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`
- `PRIMARY_PROVIDER=openrouter`

### 3. Contribution Workflow
1.  **Pull latest changes**:
    ```bash
    git pull origin version-1.1
    ```
2.  **Create a feature branch**:
    ```bash
    git checkout -b feature/my-new-feature
    ```
3.  **Commit changes**:
    - Use semantic commit messages (e.g., `feat:`, `fix:`, `docs:`).
    - Example: `feat: Add caching to local whisper provider`
4.  **Push and PR**:
    ```bash
    git push origin feature/my-new-feature
    # Open Pull Request targeting version-1.1
    ```

## Version Control Best Practices implemented
- **.gitignore**: Configured to exclude secrets (`.env`, keys), build artifacts (`dist/`, `__pycache__`), and large files.
- **Secrets Management**: `temp_ssh_key` files are removed from the index to prevent accidental leakage.
- **Commit History**: Atomic commits with descriptive messages.
