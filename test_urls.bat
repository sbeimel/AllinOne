@echo off
echo Testing different URL patterns...

echo.
echo Testing get.php with m3u_plus:
curl -s -I "http://jexhammer:vmesa123@rico.goip.de:61095/get.php?username=jexhammer&password=vmesa123&type=m3u_plus&output=ts"

echo.
echo Testing player_api.php:
curl -s -I "http://jexhammer:vmesa123@rico.goip.de:61095/player_api.php?username=jexhammer&password=vmesa123&action=get_live_categories"

echo.
echo Testing portal list:
curl -s "http://jexhammer:vmesa123@rico.goip.de:61095/player_api.php?username=jexhammer&password=vmesa123&action=get_live_categories" | head -20

pause