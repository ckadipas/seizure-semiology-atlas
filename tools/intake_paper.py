#!/usr/bin/env python3
"""Point paper submissions to the maintained, nonintegrating intake route."""

SUBMISSION_URL = (
    "https://github.com/ckadipas/seizure-semiology-atlas/issues/"
    "new?template=new-paper.yml"
)


def main() -> None:
    print("Submit a paper using the public intake form:")
    print(SUBMISSION_URL)
    print()
    print("Provide one DOI, stable link, or permitted attachment; a note is optional.")
    print("Maintainers process approved submissions through the private manuscript-ledger intake route.")
    print("This public command does not copy, inspect, queue, integrate, or publish source material.")


if __name__ == "__main__":
    main()
