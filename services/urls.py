from __future__ import annotations

from betabox_robotics.services.platform_information import (
    NetworkInformation,
    collect_network_information,
)


def print_urls(network: NetworkInformation) -> None:
    print()
    print("Betabox Network Addresses")
    print("========================")
    print()

    print("Hostname:", network.hostname)
    print()

    print("Student Web Access")
    print("------------------")

    for url in network.web_urls:
        print(f"  {url}")

    print()
    print("Direct Service Access")
    print("---------------------")

    for label, urls in (
        ("Launchpad", network.launchpad_urls),
        ("JupyterHub", network.jupyterhub_urls),
        ("Vision", network.vision_urls),
    ):
        print()
        print(f"{label}:")

        for url in urls:
            print(f"  {url}")

    print()


def main(argv: list[str] | None = None) -> int:
    if argv:
        raise ValueError("urls does not accept arguments")

    network = collect_network_information()

    print_urls(network)

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
