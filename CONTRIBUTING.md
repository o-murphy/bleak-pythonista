# **Contributing Guide 👋**

We welcome contributions to this project! To make the collaboration process as smooth and efficient as possible, please
familiarize yourself with these guidelines.

## **Getting Started**

1. **Fork the repository**: Create your own copy of the repository.
2. **Clone your fork**: Clone the repository to your local machine.
   ```shell
   git clone https://github.com/YOUR_USERNAME/bleak-pythonista.git
   cd bleak-pythonista
   ```
   > [!IMPORTANT]
   > This project uses `uv` as a dependency management tool.

3. **Install `uv`** (if you don't have it already).
   ```shell
   pip install uv
   ```

4. **Create a virtual environment**: It is recommended to use a virtual environment to isolate dependencies.
   ```shell
   uv venv .venv
   source .venv/bin/activate  # macOS/Linux
   # .venv\\Scripts\\activate  # Windows
   ```

5. **Install all dependencies**, including the development groups. The `pyproject.toml` file defines the dev group.
   ```shell
   uv sync --dev
   ```
   This command installs both the core dependencies and the development tools.

## **Running Tests**

We use `pytest` for running tests.

* To run all tests, execute:
   ```shell
   pytest
   ```

* The `pytest` configuration is located in the `pyproject.toml` file.

## **Type Checking**

We use `mypy` for static type checking.

* To run the type checks, execute:
   ```shell
   mypy src
   ```

* The `mypy` configuration is in `pyproject.toml` and specifies checking the `bleak_pythonista` package.

## **Pre-Commit Checks**

> [!NOTE]
> This project uses `pre-commit` to automatically run code formatting and style checks before each commit. This helps
maintain high code quality.

1. **Install the `pre-commit` hooks**:
   ```shell
   pre-commit install
   ```

2. **What does `pre-commit` do?**: It automatically runs tools like `ruff`, `mypy`. The
   `.pre-commit-config.yaml` file contains the full list of hooks being used.

3. Manually run `pre-commit` hooks
   ```shell
   pre-commit run --all-files
   ```

4. If a hook fails, `pre-commit` will abort the commit. Fix the errors, add the changed files (git add ...), and try to
   commit again.

## **Contribution Process**

1. **Create a branch**: Create a new branch for your changes.
   ```shell
   git checkout \-b feature/your-feature-name
   ```
2. **Make your changes**: Write your code, add new tests if necessary, and update the documentation.

3. **Commit your changes**:
   ```shell
   git add .
   git commit \-m "feat: Add a brief description of your changes"
   ```

4. **Push your branch to your fork**:
   ```shell
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**: Go to GitHub and create a Pull Request from your branch to the main branch of the original
   repository.

Thank you for your contribution! 🙏
