import sys
import select
import termios
import tty
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

def read_key(timeout=0.05):
    key_id = sys.stdin.fileno()
    old_settings = termios.tcgetattr(key_id)
    try:
        tty.setraw(key_id)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            key = sys.stdin.read(1)
            if key == '\x1b':
                key += sys.stdin.read(2)
        else:
            key = ''
    finally:
        termios.tcsetattr(key_id, termios.TCSADRAIN, old_settings)
    return key


class DroneController(Node):

    def __init__(self):
        super().__init__("drone_teleop")
        self.publisher = self.create_publisher(Twist, "/X3/cmd_vel", 10)
        self.enable_pub = self.create_publisher(Bool, "/X3/velocity_controller/enable", 10)
        self.get_logger().info("STARTED")

    def takeoff(self):
        self.get_logger().info("arming and taking off now")
        
        enable_msg = Bool()
        enable_msg.data = True
        self.enable_pub.publish(enable_msg)

        twist = Twist()
        twist.linear.z = 0.8  # Stronger upward burst to reach stable altitude

        for _ in range(25):
            self.enable_pub.publish(enable_msg)
            self.publisher.publish(twist)
            time.sleep(0.1)

        # Neutralize vertical velocity to lock hover
        twist.linear.z = 0.0
        self.publisher.publish(twist)
        self.get_logger().info("hovering in place")

    def key_binds(self, x=0.0, z=0.0, yaw=0.0):
        twist = Twist()
        twist.linear.x = float(x)
        twist.linear.z = float(z)
        twist.angular.z = float(yaw)
        self.publisher.publish(twist)


def main():
    rclpy.init()
    drone = DroneController()
    drone.takeoff()

    print("""
    Key binds:
    up arrow   : move frwd
    down arrow : move bckwd
    left arrow : yaw left
    right arrow: yaw right
    w          : ascend
    s          : descend
    no keys    : hover
    q          : quit
    """)

    try:
        while True:
            key = read_key(timeout=0.05)

            if key == "\x1b[A":      # Up Arrow
                drone.key_binds(x=0.8, z=0.0, yaw=0.0)
            elif key == "\x1b[B":    # Down Arrow
                drone.key_binds(x=-0.8, z=0.0, yaw=0.0)
            elif key == "\x1b[D":    # Left Arrow
                drone.key_binds(x=0.0, z=0.0, yaw=0.8)
            elif key == "\x1b[C":    # Right Arrow
                drone.key_binds(x=0.0, z=0.0, yaw=-0.8)
            elif key.lower() == "w": # Ascend
                drone.key_binds(x=0.0, z=0.5, yaw=0.0)
            elif key.lower() == "s": # Descend
                drone.key_binds(x=0.0, z=-0.5, yaw=0.0)
            elif key.lower() == "q": # Quit
                break
            else:
                # Key released: lock horizontal/vertical speeds to 0 to hover
                drone.key_binds(x=0.0, z=0.0, yaw=0.0)

    except Exception as error:
        print(error)

    finally:
        drone.key_binds(0.0, 0.0, 0.0)
        drone.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()