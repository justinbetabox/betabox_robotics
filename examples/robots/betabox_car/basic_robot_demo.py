from time import sleep

from betabox_robotics import BetaboxCar


def main():
    with BetaboxCar() as car:
        print("Starting vision")
        car.start_vision()
        sleep(1)

        print("Driving forward")
        car.forward(30)
        sleep(1)

        print("Stopping")
        car.stop()

        distance = car.distance()
        print(f"Distance: {distance:.2f} cm")

        snapshot = car.capture("picture.jpg")
        print(f"Saved snapshot: {snapshot.path}")


if __name__ == "__main__":
    main()
