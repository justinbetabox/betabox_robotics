from betabox_robotics import Robot


def main() -> None:
    car = Robot.default()

    snapshot = car.snapshot()

    print()
    print("Snapshot saved")
    print("==============")
    print(snapshot.path)


if __name__ == "__main__":
    main()
