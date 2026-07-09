from time import sleep

from betabox_robotics import Robot


def main() -> None:
    car = Robot.default()

    print("Detection status:")
    print(car.detection_status())

    print()
    print("Enabling color detection...")
    car.enable_detection("color")

    sleep(2)

    metadata = car.metadata("color")

    print()
    print("Latest color metadata")
    print("=====================")
    print(metadata)

    print()
    print("Disabling color detection...")
    car.disable_detection("color")


if __name__ == "__main__":
    main()
