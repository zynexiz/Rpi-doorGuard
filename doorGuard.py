from sense_hat import SenseHat
from email.message import EmailMessage
from datetime import datetime
import time, smtplib

def sendMailMessage(body):
	#Set the sender email and password and recipient emaiç
	from_email_addr ="<from address>"
	from_email_pass ="<password>"
	to_email_addr ="<send mail to>"
	timestamp = str(datetime.now())
	body = timestamp + body

	# Create a message object and build the e-mail content
	msg = EmailMessage()
	msg.set_content(body)
	msg['From'] = from_email_addr
	msg['To'] = to_email_addr
	msg['Subject'] = 'Doorguard alert'

	try:
		# Connecting to server and sending email
		# Edit the following line with your provider's SMTP server details
		server = smtplib.SMTP('smtp.gmail.com', 587)
	
		# Comment out the next line if your email provider doesn't use TLS
		server.starttls()
	
		# Login to the SMTP server and send the message
		server.login(from_email_addr, from_email_pass)
		server.send_message(msg)
		server.quit()
	except:
		writeToLog("ERROR! Can't send mail. Check configuration.")
		
# Log events in the system (make sure it has the right permissions to write to the file)
def writeToLog(message):
	logPath = "/var/log/"
	timestamp = str(datetime.now())
	with open(logPath + 'eventlogs.log', 'a') as file:
		file.write(timestamp + " - " + message +"\n")
	return

# Initialize the senseHat and define all the shapes that will be displayed on the LED matrix
def hatInit():
	global sense, unlock, lock, warning

	sense = SenseHat()
	sense.set_imu_config(True,True,True) #Compass, gyroscope, accelerometer

	r = (255, 0, 0)
	g = (0, 255, 0)
	w = (150, 150, 150)
	e = (0, 0, 0)

	unlock = [
	e,e,e,e,e,e,e,e,
	e,e,e,g,g,e,e,e,
	e,e,g,e,e,g,e,e,
	e,e,g,e,e,e,e,e,
	e,g,g,g,g,g,g,e,
	e,g,g,g,g,g,g,e,
	e,g,g,g,g,g,g,e,
	e,e,e,e,e,e,e,e,
	]

	lock = [
	e,e,e,e,e,e,e,e,
	e,e,e,r,r,e,e,e,
	e,e,r,e,e,r,e,e,
	e,e,r,e,e,r,e,e,
	e,r,r,r,r,r,r,e,
	e,r,r,r,r,r,r,e,
	e,r,r,r,r,r,r,e,
	e,e,e,e,e,e,e,e,
	]

	warning = [
	e,e,e,r,r,e,e,e,
	e,e,r,r,r,r,e,e,
	e,e,r,r,r,r,e,e,
	e,e,r,r,r,r,e,e,
	e,e,e,r,r,e,e,e,
	e,e,e,r,r,e,e,e,
	e,e,e,e,e,e,e,e,
	e,e,e,r,r,e,e,e,
	]
	return

# Let the user set the lock/unlock pattern
def setPassPattern():
	global pattern
	pattern_num = 0
	pattern = []
	sense.show_message("Set code!")
	sense.stick.get_events().clear()

	while True:
		# Display the length of the pattern. NOTE! The senseHAT can not display any number above 9!
		if len(pattern) <= 9:
			sense.show_letter(str(pattern_num))
		sequence = sense.stick.wait_for_event()
		# If the user presses the middle stick, the pattern is stored. Make sure the pattern length is at least 1.
		if sequence.direction == 'middle' and len(pattern) > 0:
			break
		# Save the input to the sequence (max 9)
		elif sequence.action == 'released':
			if len(pattern) <= 9:
				pattern.append(sequence.direction)
				pattern_num += 1

	sense.show_message("Saved!")
	return

# Calculate distance between two angels. Returns the distance in degrees.
def getDistance(ang1, ang2):
	phi = abs(ang2-ang1) % 360
	if phi > 180:
		phi = 360 - phi
	return phi

## Main program
#
#

hatInit()
setPassPattern()

sense.set_pixels(unlock)
locked = False
sequence = []
tick = 0
alarmTick = 0
triggerAlarm = False
sense.stick.get_events().clear()

while True:
	for joySeq in sense.stick.get_events():
		# If joystick is held in unlocked mode, set new code pattern
		if joySeq.direction == "middle" and joySeq.action == "held" and not locked:
			setPassPattern()
			sequence = []
		# If joystick middle pressed, check if the pattern match
		elif joySeq.direction == "middle" and joySeq.action == "released":
			if sequence == pattern:
				if not locked:
					for i in range(9,0,-1):
						sense.show_letter(str(i))
						time.sleep(1)
				# Toggle lock status and get sensor orientation
				locked = not locked
				writeToLog("Lock status: " + str(locked))
				lockedOrientation = sense.get_orientation()['yaw']
			else:
				# Display warning if pattern don't match
				sense.set_pixels(warning)
				time.sleep(2)

			sequence = []

		#If the user presses a direction on the stick, this is saved as a sequence
		elif joySeq.action == "pressed" and joySeq.direction != "middle":
			sequence.append(joySeq.direction)

		# Display the lock status and reset tick timer
		sense.stick.get_events().clear()
		if triggerAlarm and locked:
			sense.set_pixels(warning)
		elif locked:
			sense.set_pixels(lock)
		else:
			sense.set_pixels(unlock)
			triggerAlarm = False

		tick = 0

	# Get current orientation and detect if angle distance from baseline value > 20 degrees
	if locked and (getDistance(sense.get_orientation()['yaw'], lockedOrientation) > 20) and not triggerAlarm:
		triggerAlarm = True
		alarmTick = 0
		sense.set_pixels(warning)
		writeToLog("Motion detected")

	# Timer in 10th of seconds. Counter for resetting entered sequence and alarm activation
	time.sleep(0.1)
	if triggerAlarm and alarmTick <= 100:
		alarmTick += 1
	tick += 1

	# After 10 sec, reset sequence pattern
	if tick == 100:
		sequence = []
		tick = 0

	# After 10 sec of triggered alarm, fire the alarm
	if alarmTick == 100:
		alarmTick = 101
		writeToLog("Alarm activated!")
		sendMailMessage("\n\nHello, \n\nAre you aware that your door was just opened? \nIf this wasn't you, maybe it's time to call the cops? \n\nBest regards, Doorguard")
