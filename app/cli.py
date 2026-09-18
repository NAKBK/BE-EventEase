import argparse

from app.core.database import get_session_factory
from app.seed import seed_demo_data


def main() -> None:
    parser = argparse.ArgumentParser(description="EventEase backend commands")
    parser.add_argument("command", choices=["seed"])
    args = parser.parse_args()

    if args.command == "seed":
        with get_session_factory()() as session:
            seed_demo_data(session)
        print("Demo seed ready")


if __name__ == "__main__":
    main()
