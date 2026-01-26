#!/bin/bash
# Timetable Assistant Bot - Convenience Run Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_usage() {
    cat << EOF
Timetable Assistant Bot - Run Script

Usage:
    ./run.sh [COMMAND] [OPTIONS]

Commands:
    telegram         Run Telegram bot
    discord          Run Discord bot
    test             Run test suite
    install          Install dependencies
    dev-install      Install with dev dependencies
    format           Format code with black and isort
    lint             Run linters (ruff, flake8)
    typecheck        Run mypy type checker
    docker-build     Build Docker images
    docker-up        Start Docker containers
    docker-down      Stop Docker containers
    docker-logs      View Docker logs

Options:
    -h, --help       Show this help message
    -d, --debug      Run with DEBUG log level
    -c, --config     Specify config file (default: configuration.yaml)

Examples:
    ./run.sh telegram
    ./run.sh discord --debug
    ./run.sh test
    ./run.sh docker-up telegram

EOF
}

check_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Warning: .env file not found${NC}"
        echo "Create one from .env.example:"
        echo "  cp .env.example .env"
        echo "Then edit .env with your bot tokens"
        echo ""
    fi
}

check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}Warning: Not running in a virtual environment${NC}"
        echo "Consider creating one:"
        echo "  python -m venv venv"
        echo "  source venv/bin/activate  # Linux/Mac"
        echo "  venv\\Scripts\\activate     # Windows"
        echo ""
    fi
}

# =============================================================================
# Commands
# =============================================================================

cmd_telegram() {
    check_env
    echo -e "${GREEN}Starting Telegram bot...${NC}"
    python -m src.main telegram "$@"
}

cmd_discord() {
    check_env
    echo -e "${GREEN}Starting Discord bot...${NC}"
    python -m src.main discord "$@"
}

cmd_test() {
    echo -e "${GREEN}Running tests...${NC}"
    pytest tests/ -v "$@"
}

cmd_install() {
    echo -e "${GREEN}Installing dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}Done!${NC}"
}

cmd_dev_install() {
    echo -e "${GREEN}Installing dev dependencies...${NC}"
    pip install -r requirements.txt -r requirements-dev.txt
    # Or use: pip install -e ".[dev]"
    echo -e "${GREEN}Done!${NC}"
}

cmd_format() {
    echo -e "${GREEN}Formatting code...${NC}"
    black src/ tests/
    isort src/ tests/
    echo -e "${GREEN}Done!${NC}"
}

cmd_lint() {
    echo -e "${GREEN}Running linters...${NC}"
    ruff check src/ tests/
    # flake8 src/ tests/  # Optional
    echo -e "${GREEN}Done!${NC}"
}

cmd_typecheck() {
    echo -e "${GREEN}Running type checker...${NC}"
    mypy src/
    echo -e "${GREEN}Done!${NC}"
}

cmd_docker_build() {
    echo -e "${GREEN}Building Docker images...${NC}"
    docker-compose build "$@"
    echo -e "${GREEN}Done!${NC}"
}

cmd_docker_up() {
    echo -e "${GREEN}Starting Docker containers...${NC}"
    docker-compose up -d "$@"
    echo -e "${GREEN}Done!${NC}"
    echo "View logs with: ./run.sh docker-logs"
}

cmd_docker_down() {
    echo -e "${GREEN}Stopping Docker containers...${NC}"
    docker-compose down
    echo -e "${GREEN}Done!${NC}"
}

cmd_docker_logs() {
    docker-compose logs -f "$@"
}

# =============================================================================
# Main Script
# =============================================================================

# No arguments 
if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

# Parse command
COMMAND=$1
shift

# Handle help flag
if [ "$COMMAND" = "-h" ] || [ "$COMMAND" = "--help" ]; then
    print_usage
    exit 0
fi

# Execute command
case $COMMAND in
    telegram)
        cmd_telegram "$@"
        ;;
    discord)
        cmd_discord "$@"
        ;;
    test)
        cmd_test "$@"
        ;;
    install)
        cmd_install "$@"
        ;;
    dev-install)
        cmd_dev_install "$@"
        ;;
    format)
        cmd_format "$@"
        ;;
    lint)
        cmd_lint "$@"
        ;;
    typecheck)
        cmd_typecheck "$@"
        ;;
    docker-build)
        cmd_docker_build "$@"
        ;;
    docker-up)
        cmd_docker_up "$@"
        ;;
    docker-down)
        cmd_docker_down "$@"
        ;;
    docker-logs)
        cmd_docker_logs "$@"
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac