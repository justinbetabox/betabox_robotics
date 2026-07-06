from time import sleep

from betabox_robotics import BetaboxCar


def main():
    with BetaboxCar() as car:
        car.audio.say("Starting robot demo")

        print("Driving forward")
        car.drive.forward(30)
        sleep(1)

        print("Stopping")
        car.drive.stop()

        distance = car.sensors.ultrasonic.distance()
        print(f"Distance: {distance} cm")

        car.audio.say("Demo complete")


if __name__ == "__main__":
    main()
