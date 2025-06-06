I'm a big fan of the weather.gov graphical forecast, but it doesn't render well on the TRMNL display, especially in a quarter of the screen.

So I picked the measurements that meant the most to me and tried to make them clear on the TRMNL's e-ink display.

![foo](https://github.com/user-attachments/assets/041752bc-919a-4bff-b17b-dc1afed5becb)

The solid black line represents the temperature and corresponds with the left y-axis.  The dashed line represents the wind speed and corresponds with the right y-axis.  Due to lack of screen real estate, labeling is kept to a minimum.  Chance of rain is represented by the light "gray" histogram at the bottom of the chart and the solid black at the very bottom represents the boolean `isDaytime` value represented in the weather service API (and I do not know why it does not correspond to local sunrise/sunset times).  Finally, wind direction is shown along the top of the chart and minimal time labels run along the bottom of the chart.

The intent is for the python script to run in a virtual environment on a web server via anacron and drop an updated `.png` in a location the TRMNL can find for updates.  The setup and teardown scripts more or less make this easy to set up.  The forecast location and destination filepath can be specefied in a simple configuration file.  The resulting png is retrieved and presented on the TRMNL via the "Image Display" plugin.
