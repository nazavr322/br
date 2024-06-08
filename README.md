# br
## Getting started
Locate your `.epub` file and run:
```sh
python -m br <path_to_the_book>
```
## Setup
### Notes
- The project uses Python 3.12
### Installation
1. Create virtual environment and install dependencies:
    ```sh
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2. Generate the `resources.py` file:
    ```sh
    rcc -g python resources.qrc | sed '0,/PySide[2|6]/s//PyQt6/' > br/resources.py
    ```
3. Create `.env` file and define required variables:
    ```sh
    cat .env.example > .env
    ```
