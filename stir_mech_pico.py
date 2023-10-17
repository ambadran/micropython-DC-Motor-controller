'''
DC Motor connected to an H-Bridge Advanced Control 

Meant for RaspberryPi Pico

see: <> for esp32s3 version
'''
from machine import Pin, PWM, Timer
from math import floor, e
from time import sleep_ms


class Dir:
    '''
    acts like an enum
    '''
    CW = True
    CCW = False


class MotorPin:
    '''
    class to handle Motor pins
    '''

    # Mapping everything to everything :D
    ON_OFF_FUNC = [Pin.value, PWM.duty_u16]
    STATE_FUNC = [Pin.value, lambda motor_pin: PWM.duty_u16(motor_pin) == 65535]
    ON_VALUE = [[1, 0], [65535, 0]]
    OFF_VALUE = [[0, 1], [0, 65535]]
    VALUES = [OFF_VALUE, ON_VALUE]
    SAMPLE_ORDER_BIT = [[-1, 1], [1, -1]]  # off/on then activehigh/low

    # other constants
    SAMPLE_TIME = 1  # ms 

    def __init__(self, pin: Pin = None, pwm: PWM = None, is_active_low: bool = None, 
            maximum_duty_cycle: int = 65535, sweep_time: int = 0, timer_ind: int=None):
        '''
        contstructor
        '''
        if pin is None and pwm is None:
            raise ValueError("Motor Pin must either be a normal pin or a pwm pin")

        if is_active_low is None:
            raise ValueError("Must speicify whether the motor pin is active high or active low")

        self.is_active_low = is_active_low

        if pin:
            self.pin_pwm_mode = 0
            self.motor_pin = pin

            # for normal pins there is not sweeping functions
            self.on = self._instantaneous_on
            self.off = self._instantaneous_off

        else:
            self.pin_pwm_mode = 1
            self.motor_pin = pwm

            self.maximum_duty_cycle = maximum_duty_cycle

            # Sweeping functions variables
            if timer_ind is None:
                raise ValueError("Must specify a distinct timer for this pwm value")
            self.timer = Timer(timer_ind)

            # initializing start index
            self.current_index = 0
                
            # here is where the .on and .off methods are assigned
            self.set_sweep_variables(sweep_time)

    @property
    def maximum_duty_cycle(self):
        '''
        duty cycle when transistor is ON
        '''
        return self._maximum_duty_cycle

    @maximum_duty_cycle.setter
    def maximum_duty_cycle(self, value):
        '''
        value in 0 to 65535
        '''

        state_before = not not self.motor_pin.duty_u16()

        self.motor_pin.duty_u16(value)
        sleep_ms(5)  # I have no idea why this method takes time to load
                     # If I don't stall for a bit, It will return the wrong
                     # duty_cycle down
                     # Fortunately, This method isn't time critical at all
                     # only run once in the begginning and by the user if needed

        # frequency affect degree of accuracy,
        # so not all choosen values are actually choosen
        actual_value = self.motor_pin.duty_u16()

        # saving an internal variable
        self._maximum_duty_cycle = actual_value

        # updating class constants with the new ACTUAL maximum_duty_cycle value
        MotorPin.ON_VALUE[1][0] = actual_value
        MotorPin.OFF_VALUE[1][1] = actual_value
        MotorPin.STATE_FUNC[1] = lambda motor_pin: PWM.duty_u16(motor_pin) == actual_value

        # get pin to its original state
        if not state_before:
            self.motor_pin.duty_u16(0)



    @property
    def state(self):
        '''
        returns whether current pin is on/off, transistor is allowing current or not

        #TODO: optimize 
            remove the not not and use a bitwise operation to return 1 if the output is >1 or 0
        '''
        return MotorPin.STATE_FUNC[self.pin_pwm_mode](self.motor_pin) ^ self.is_active_low

    def _instantaneous_on(self):
        '''
        This method is not supposed to be called directly by user, instead upon setting sweep_time in Motor Object initiation
        a .on or .off variable will be assigned to point to ._instantaneous_on/off or ._sweep_on/off methods 

        turns pin fully on, aka transistor allow current through

        This function is maps pin_pwm_mode and is_active_low to the correct function that will turn on the motor pin
        '''
        MotorPin.ON_OFF_FUNC[self.pin_pwm_mode](self.motor_pin, MotorPin.ON_VALUE[self.pin_pwm_mode][self.is_active_low])

    def _instantaneous_off(self):
        '''
        This method is not supposed to be called directly by user, instead upon setting sweep_time in Motor Object initiation
        a .on or .off variable will be assigned to point to ._instantaneous_on/off or ._sweep_on/off methods 


        turns pin fully off, aka transistor doesn't allow current through

        This function is maps pin_pwm_mode and is_active_low to the correct function that will turn off the motor pin
        '''
        MotorPin.ON_OFF_FUNC[self.pin_pwm_mode](self.motor_pin, MotorPin.OFF_VALUE[self.pin_pwm_mode][self.is_active_low])

    def set(self, value: bool):
        '''

        turns pins to value
        
        This function is maps value(on or off), pin_pwm_mode and is_active_low to the correct function that will 
            turn the motor pin on or off 
        
        :param value: must be boolean-like value. e.g- 0/1 or False/True
        '''
        if value:
            self.on()
        else:
            self.off()
        # MotorPin.ON_OFF_FUNC[self.pin_pwm_mode](self.motor_pin, MotorPin.VALUES[value][self.pin_pwm_mode][self.is_active_low])

    def duty(self, value: int):
        '''
        sets PWM pins to wanted duty cycle
        '''
        self.motor_pin.duty(value)

    def set_sweep_variables(self, sweep_time: int):
        '''
        :time in ms!!!!

        sets the variables when the motor.sweep_time is set
        This is to not do complex computation every time we call .sweep_on()
        #TODO: implement exponential set points instead of linear as DC motor is like that
        '''
        # try:
        #     m = 1/sweep_time

        #     # try sweep/sample = 10/2.x
        #     # must always have number rounded down then add the 10 at the end manually in any case
        #     self.num_samples = floor(sweep_time/MotorPin.SAMPLE_TIME)

        #     samples = []
        #     for ind in range(0, self.num_samples):
        #         samples.append(int(m*ind*MotorPin.SAMPLE_TIME*self.maximum_duty_cycle))

        #     # Adding maximum value to ensure extremes are covered when uneven samples
        #     samples.append(self.maximum_duty_cycle)

        #     # inversing list order if necessary
        #     self.samples_off = samples[::MotorPin.SAMPLE_ORDER_BIT[0][self.is_active_low]]
        #     self.samples_on = samples[::MotorPin.SAMPLE_ORDER_BIT[1][self.is_active_low]]

        #     # setting the on function, the function that will be used by user
        #     self.on = self._sweep_on
        #     self.off = self._sweep_off

        # except ZeroDivisionError:
        #     # setting the on function, the function that will be used by user
        #     self.on = self._instantaneous_on
        #     self.off = self._instantaneous_off
        
        #TODO: test the shit out of this >:)
        try:
            m = (e+1)/sweep_time

            # try sweep/sample = 10/2.x
            # must always have number rounded down then add the 10 at the end manually in any case
            self.num_samples = floor(sweep_time/MotorPin.SAMPLE_TIME)

            self.samples_on = []
            self.samples_off = []
            for ind in range(0, self.num_samples+1):
                # Equation derivation and graphs in iPad notes
                self.samples_off.append(-e**(m*ind*MotorPin.SAMPLE_TIME -1 -e) + 1)
                self.samples_on.append(-e**(-m*ind*MotorPin.SAMPLE_TIME) + 1)

            # The expoenential equations I set is upto 97.57% of the value
            # So must add the 65535 manually
            self.samples_off.insert(0, self.maximum_duty_cycle)
            self.samples_on.append(self.maximum_duty_cycle)
            self.num_samples += 1  # I added a value so must samples++

            # Reverse for is_active_low
            self.samples_off = self.samples_off[::MotorPin.SAMPLE_ORDER_BIT[0][self.is_active_low]]
            self.samples_on = self.samples_on[::MotorPin.SAMPLE_ORDER_BIT[1][self.is_active_low]]

            # setting the on function, the function that will be used by user
            self.on = self._sweep_on
            self.off = self._sweep_off

        except ZeroDivisionError:
            # setting the on function, the function that will be used by user
            self.on = self._instantaneous_on
            self.off = self._instantaneous_off

    def _update_pwm_duty_cycle_sweep_on(self, x):
        '''
        :param x: redundant variable for Timer class 
        ISR function for Timer1, gets executed every MotorPin.SAMPLE_TIME, until samples list is finished
        '''
        self.motor_pin.duty_u16(self.samples_on[self.current_index])
        self.current_index += 1
        if self.current_index > self.num_samples:
            self.current_index = 0
            self.timer.deinit()

    def _sweep_on(self):
        '''
        This method is not supposed to be called directly by user, instead upon setting sweep_time in Motor Object initiation
        a .on or .off variable will be assigned to point to ._instantaneous_on/off or ._sweep_on/off methods 

        sweeps PWM to wanted signal
        '''
        self.timer.init(mode=Timer.PERIODIC, period=MotorPin.SAMPLE_TIME, callback=self._update_pwm_duty_cycle_sweep_on)

    def _update_pwm_duty_cycle_sweep_off(self, x):
        '''
        :param x: redundant variable for Timer class 
        ISR function for Timer1, gets executed every MotorPin.SAMPLE_TIME, until samples list is finished
        '''
        self.motor_pin.duty_u16(self.samples_off[self.current_index])
        self.current_index += 1
        if self.current_index > self.num_samples:
            self.current_index = 0
            self.timer.deinit()

    def _sweep_off(self):
        '''
        This method is not supposed to be called directly by user, instead upon setting sweep_time in Motor Object initiation
        a .on or .off variable will be assigned to point to ._instantaneous_on/off or ._sweep_on/off methods 

        sweeps PWM to wanted signal
        '''
        self.timer.init(mode=Timer.PERIODIC, period=MotorPin.SAMPLE_TIME, callback=self._update_pwm_duty_cycle_sweep_off)

    def __repr__(self):
        return f"{repr(self.motor_pin)}, state: {self.state}"

    def __str__(self):
        return f"{str(self.motor_pin)}, state: {self.state}"


class Motor:
    '''
    H-Bridge controller for DC motors

    Pin definitions:

    v1          v2
    |           |
    |           |
    |           |
    +---o   o---+
    |           |
    |           |
    |           |
    g1          g2

    This class ultimate goal is let user turn on/off each pin REGARDLESS of whether they are active low/high
    using vx or gx .on() or .off()
    
    Also all pins have .state(value) where value is (0 or 1) or (False or True)
    
    Also g1 and g2 are actually PWM pins so their .on() is just 100% duty cycle,
    They have .partial_on() for a 'maximum_duty_cycle' argument set by user
    They also have .duty(value) to set a particular duty_cycle


    #TODO: rename p1, p2, n1, n2 to pins 1, 2, 3, 4
        this is to include h-bridges made of 4 npns for example

        differentiate between the underlying self.p1 (should be renamed to self._p1)
        and the wanted transistor control

        should only be controlled with .on() or .off(), the active high/active low should be
        pre-choosen by the user

        make .partial_on() for pwm pins (or sth)

    '''

    def __init__(self, v1_pin_num: int, v2_pin_num: int, g1_pin_num: int, g2_pin_num: int, 
                 v1_active_low: bool, v2_active_low: bool, g1_active_low: bool, g2_active_low: bool,
                 maximum_duty_cycle: int = 65535, sweep_time: int = 0, pwm_freq: int = 20000):
        '''
        Constructor
        :param maximum_duty_cycle: its default is set in class variables ON_VALUE and OFF_VALUE in MotorPin, if it's assigned it will be assigned there too
        :param sweep_time: in ms, is the time where PWM turns from one state to the other
        '''
        #TODO: type check and range check everything

        # dictionary to map cw_ccw value to corresponding activating cw/ccw method
        self.cw_func = {Dir.CW: self.cw, Dir.CCW: self.ccw}

        # low-level Motor control pin variables
        self._v1_pin = Pin(v1_pin_num, Pin.OUT)
        self._v2_pin = Pin(v2_pin_num, Pin.OUT)
        self._g1_pwm = PWM(Pin(g1_pin_num))
        self._g1_pwm.freq(pwm_freq)  # pico can't set freq in init
        self._g2_pwm = PWM(Pin(g2_pin_num))
        self._g2_pwm.freq(pwm_freq)  # pico can't set freq in init

        # User Motor control pins
        self.v1 = MotorPin(pin = self._v1_pin, is_active_low = v1_active_low, 
                sweep_time=sweep_time)
        self.v2 = MotorPin(pin = self._v2_pin, is_active_low = v2_active_low,
                 sweep_time=sweep_time)
        self.g1 = MotorPin(pwm = self._g1_pwm, is_active_low = g1_active_low,
                 sweep_time=sweep_time, maximum_duty_cycle=maximum_duty_cycle,
                 timer_ind=-1)  # no timer IDs in pico
        self.g2 = MotorPin(pwm = self._g2_pwm, is_active_low = g2_active_low,
                 sweep_time=sweep_time, maximum_duty_cycle=maximum_duty_cycle,
                 timer_ind=-1)  # no timer IDs in pico

        # must initialize internal variable nonetheless
        self._sweep_time = sweep_time
        self._maximum_duty_cycle = maximum_duty_cycle

        # Initializing with motor off
        self.off()

        # Default state is Clockwise
        self._cw_ccw: bool = Dir.CW 

    @property
    def sweep_time(self):
        '''
        return inner sweep_time
        '''
        return self._sweep_time

    @sweep_time.setter
    def sweep_time(self, value):
        '''
        sets the inner variables needed to execute PWM sweeping in MotorPin class
        sweep time is the time where PWM turns from one state to the other

        NOTE: assigning this variable will call
        .set_sweep_on_variables() and .set_sweep_off_variables() of the PWM MotorPins
        which in turn assigns the .on() method to ._instantaneous_on/off or ._sweep_on/off
        and also calculates needed variables for PWM sweeping algorithm to work properly
        '''
        self.g1.set_sweep_variables(value)
        self.g2.set_sweep_variables(value)
        self._sweep_time = value

    @property
    def maximum_duty_cycle(self):
        '''
        duty cycle when transistor is ON
        '''
        return self._maximum_duty_cycle

    @maximum_duty_cycle.setter
    def maximum_duty_cycle(self, value):
        '''
        value in 0 to 65535
        '''
        self._maximum_duty_cycle = value
        self.g1.maximum_duty_cycle = value
        self.g2.maximum_duty_cycle = value

    def on(self):
        '''
        activates H-bridge to the last known cw_ccw value
        '''
        self.direction = self._cw_ccw

    def off(self):
        '''
        deactivates H-bridge
        '''
        if self.v1.state:

            # prevent shorts
            self.g1._instantaneous_off() 
            
            # Turning motor power off
            if self.g2.state:
                self.g2.off()
                # without this +1, the ._instantaneous_on won't work for some reason ?!??!!
                sleep_ms(self.sweep_time+1) 

            self.v1.off()
            self.v2.off() # just in case

        elif self.v2.state:

            # prevent shorts
            self.g2._instantaneous_off()

            # Turning motor power off
            if self.g1.state:
                self.g1.off()
                # without this +1, the ._instantaneous_on won't work for some reason ?!??!!
                sleep_ms(self.sweep_time+1)

            self.v2.off()
            self.v1.off() # just in case

        # grounding both motor pins
        self.g1._instantaneous_on()
        self.g2._instantaneous_on()

    @property
    def is_on(self):
        '''
        returns whether motor is on or off
        '''
        return (self.v1.state and self.g2.state) or (self.v2.state and self.g1.state)

    def cw(self):
        '''
        clockwise motion

        #TODO: try to make a routine that takes into consideration short circuits more without adding too much logic
        '''
        if self.g2.state:
            self.g2.off()
            sleep_ms(self.sweep_time)

        self.v1.off()

        self.v2.on()
        
        if not self.g1.state:
            self.g1.on()
            sleep_ms(self.sweep_time)

        # Saving current state
        self._cw_ccw = True

    def ccw(self):
        '''
        anti-clockwise motion
        '''
        if self.g1.state:
            self.g1.off()
            sleep_ms(self.sweep_time)

        self.v2.off()

        self.v1.on()

        if not self.g2.state:
            self.g2.on()
            sleep_ms(self.sweep_time)

        # Saving current state
        self._cw_ccw = False

    @property
    def direction(self):
        '''
        returns current cw_ccw
        '''
        return self._cw_ccw

    @direction.setter
    def direction(self, value: bool):
        '''
        sets motor direction
        '''
        self.cw_func[value]()

    def toggle_dir(self):
        '''
        toggles the direction of motor
        '''
        self.direction = not self._cw_ccw

    def __repr__(self):
        '''
        also return string representation :D
        '''
        return str(self)

    def __str__(self):
        '''
        string representation
        '''
        if self.is_on:
            string_dir = 'CW' if self._cw_ccw else 'CCW'
            return f"Motor is ON, moving {string_dir}, V1: {self.v1.state}, V2: {self.v2.state}, G1: {self.g1.state}, G2: {self.g2.state}"

        else:
            return f"Motor is OFF, V1: {self.v1.state}, V2: {self.v2.state}, G1: {self.g1.state}, G2: {self.g2.state}"


class LimitSwitch:
    '''
    Class to handle interfacing of limit switches

    NB: ISR here is specifically implemented to change motor direction to a specific orientation
    '''
    def __init__(self, pin_num: int, motor_object: Motor, motor_dir: bool):
        '''
        constructor
        '''
        # initializing pin
        self.irq_pin = Pin(pin_num, Pin.IN)

        # Setting interrupt service routine method
        self.motor: Motor = motor_object

        if motor_dir == Dir.CW:
            self._motor_func = self.motor.cw

        elif motor_dir == Dir.CCW:
            self._motor_func = self.motor.ccw

        # Activating IRQ pin
        self.activate_irq()
        
        # Timer variable
        self.timer = Timer(-1)  # pico doesn't support Timer IDs

        # Tracking variable
        self.is_activated = False

    def _ISR(self):
        '''
        I Must call the _motor_func from this to add the buffer argument

        This does add a function call to the ISR
        #TODO: make specific method in Motor for calling in ISR
        '''
        if not self.is_activated:

            self.timer.init(period=50, mode=Timer.ONE_SHOT, callback=lambda t: self.reset_activated_status())

            #TODO: this is a temporary fix for the Pin.IRQ_FALLING not working properly!!!!!
            # Pin(15) persists on calling in both rising and falling, when i poll it, it's as if it remembers that it
            # was low and doesn't execute the return None, ?!??!?!!!!!!!!!
            if self.irq_pin.value():
                # Do nothing when it's detecting a rising edge
                return None

            self._motor_func()
            self.is_activated = True
            print('irq happenned', self.irq_pin, '\n')  #TODO: remove this after extensive testing


        # As measured from oscilloscope the limit switches bounces for about 700 ms
        # So to deal with it, will deactivate IRQ for 1ms
        # The timer solution didn't, I think the IRQ raised while function is being processed?!?


    def reset_activated_status(self):
        self.is_activated = False

    def _fake_ISR(self):
        '''
        There is no clear way to disable a specific IRQ, and disabling all IRQ compromises rshell
        This is a nop function to execute for when I don't want the IRQ
        '''
        pass

    def deactivate_irq(self):
        self.irq_pin.irq(handler=lambda t: self._fake_ISR())

    def activate_irq(self):
        self.irq_pin.irq(handler =lambda t: self._ISR(), trigger = Pin.IRQ_FALLING)


class StirringMechanism:
    '''
    Class to handle the Whole Mechanism
    '''
    def __init__(self, motor: Motor, limit_sw1: LimitSwitch, limit_sw2: LimitSwitch):
        '''
        Constructor
        '''
        self.motor = motor
        self.limit_sw1 = limit_sw1
        self.limit_sw2 = limit_sw2

    def on(self):
        '''
        activate IRQ
        '''
        self.limit_sw1.activate_irq()
        self.limit_sw2.activate_irq()

    def off(self):
        '''
        deactivate motor and IRQ
        '''
        self.limit_sw1.deactivate_irq()
        self.limit_sw2.deactivate_irq()
        motor.off()

    def monitor(self):
        '''
        prints current motor dir and last limit switch triggered
        '''
        while True:
            print(f"Motor dir: {self.motor._cw_ccw} \r")

# Object Initializations
# sweep_time = 100  # in ms
motor = Motor(v1_pin_num=4, v2_pin_num=5, g1_pin_num=6, g2_pin_num=7, v1_active_low=False, v2_active_low=False, g1_active_low=True, g2_active_low=True, sweep_time=100, pwm_freq=1000)
limit_sw1 = LimitSwitch(17, motor, Dir.CW)
limit_sw2 = LimitSwitch(16, motor, Dir.CCW)
sr = StirringMechanism(motor, limit_sw1, limit_sw2)




