from time import sleep

from betabox_robotics import Robot


def main() -> None:
    car = Robot.default()

    print("Starting recording...")
    path = car.start_recording()
    print(path)

    sleep(5)

    print("Stopping recording...")
    recording = car.stop_recording()

    print()
    print("Recording saved")
    print("===============")
    print(recording.path)
    print(f"Frames:   {recording.frame_count}")
    print(f"Duration: {recording.duration:.1f}s")


if __name__ == "__main__":
    main()
