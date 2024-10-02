system_python := "python3"
python := ".venv/bin/python3"


setup:
    #!/usr/bin/env sh
    if test ! -e .venv; then
        {{ system_python }} -m venv .venv
        {{ python }} -m pip install --upgrade pip
        {{ python }} -m pip install -r ./requirements.txt
    fi


check-local:
    #!/usr/bin/env sh
    if ! command -v socat > /dev/null; then
        echo "Error: socat is not installed." >&2
        exit 1
    fi


run REMOTE_PATH DEST_SOCKET="./node.socket": setup check-local 
    {{python}} -m bind_remote_socket {{DEST_SOCKET}} {{REMOTE_PATH}}
