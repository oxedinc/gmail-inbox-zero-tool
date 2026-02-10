# InboxZero Tool (Gmail Label Manager)

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

<img width="100%" alt="CleanShot 2026-02-10 at 17 02 11@2x" src="https://github.com/user-attachments/assets/412ae1d0-e852-4d4d-aa0d-6d68df73da62" />

**InboxZero Tool** is a powerful desktop application designed to help you clean up your Gmail inbox, reach **Inbox Zero**, and organize your digital life efficiently. It leverages the **Gmail API** to perform deep cleaning, advanced filtering, and bulk management tasks that the standard Gmail interface makes difficult.

## Key Features

-   **🧹 Deep Clean & Permanent Delete**: Bypass the Trash folder to instantly delete thousands of emails and free up storage space.
-   **🔍 Advanced Search**:
    -   **Regex Filtering**: Use Python Regular Expressions (e.g., `^no-reply.*`) to filter senders locally.
    -   **Flexible Date Ranges**: Quickly filter by "Last Month", "Last Year", or custom periods.
-   **📊 Top Senders Analysis**: Discover who is filling up your inbox.
-   **🖱️ Context Menu Actions**: Right-click on any sender to:
    -   View all their emails.
    -   Create a filter instantly.
    -   Copy their address.
-   **🏷️ Label & Filter Management**: Create, rename, delete, and list labels and filters with ease.
-   **📂 Large File Finder**: One-click search for emails larger than 10MB.
-   **🗑️ Empty Trash**: Permanently delete all emails in the Trash folder.

> **⚠️ Warning**: This tool performs **destructive actions** (permanent deletion). Use with caution and verify your queries before executing bulk actions.

---

## Screenshots

<img width="100%" alt="CleanShot 2026-02-10 at 17 02 49@2x" src="https://github.com/user-attachments/assets/3c1a841b-f202-4c96-b1a8-97afd9639169" />

---

## Installation

### Prerequisites

-   **Python 3.9+**
-   **Gmail API Credentials** (OAuth 2.0 Client ID for Desktop).

### Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/oxedinc/gmail-inbox-zero-tool.git
    cd gmail-inbox-zero-tool
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -e .
    ```

4.  **Configure Credentials**:
    -   Place your `credentials.json` file in the `credentials/` folder.
    -   On first run, a browser window will open to authorize the app.

## Usage

Run the application:

```bash
python run.py
```

### Tips
-   **Search Tab**: Use this for analysis. Right-click on results to take action.
-   **Regex Field**: Enter a Python regex pattern (e.g., `@newsletter\.com`) to filter the "Top Senders" list.
-   **Query Field (`q`)**: Accepts standard Gmail search operators (e.g., `is:unread`, `larger:5M`).

## Project Structure

```text
gmail_label_manager/
├── src/gmail_manager/  # Source code
├── credentials/        # OAuth credentials (ignored by git)
├── tests/              # Unit tests
├── run.py              # Entry point
└── README.md           # Documentation
```

## Tags

`python`, `gmail-api`, `email-cleaner`, `inbox-zero`, `tkinter`, `gui`, `email-optimization`, `productivity`, `spam-filter`, `regex-search`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
