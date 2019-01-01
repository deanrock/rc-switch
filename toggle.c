/*
$ gcc -Wall -pthread -o toggle toggle.c -lpigpio -lrt && ./toggle 1010011001100110101001100110010101010101101001010e
*/
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pigpio.h>
#include <unistd.h>

int main (int argc, char *argv[])
{
   if (argc != 2) {
      printf("wrong arg count\n");
      exit(1);
   }

   char *input = argv[1];
   if (strlen(input) != 50) {
      printf("arg 1 requires 50 characters\n");
      exit(1);
   }

   if (gpioInitialise() < 0) {
      return 1;
   }

   int gpio = 18;
   gpioSetMode(gpio, PI_OUTPUT);
   gpioWrite(gpio, PI_OFF);

   gpioPulse_t pulse[50*8];

   int iter=0;
   for (int j=0;j<8;j++) {
      int state = 1;

      int i = 0;
      for (;i < 50;i ++) {
         if (state) {
            pulse[iter].gpioOn = (1<<gpio);
            pulse[iter].gpioOff = 0;
         }else{
            pulse[iter].gpioOn = 0;
            pulse[iter].gpioOff = (1<<gpio);
         }

         int wait = 0;
         switch(input[i]) {
            case '0': wait = 230; break;
            case '1': wait = 900; break;
            case 'e': wait = 8700; break;
         }
         pulse[iter].usDelay = wait;

         iter++;
         state = !state;
      }
   }

   gpioWaveAddNew();
   gpioWaveAddGeneric(8*50, pulse);

   int wave_id = gpioWaveCreate();

   if (wave_id >= 0)
   {
      gpioWaveTxSend(wave_id, PI_WAVE_MODE_ONE_SHOT);

      while (gpioWaveTxBusy()) time_sleep(0.1);
   }
   else
   {
      printf("err\n");
   }
   
   gpioWrite(gpio, PI_OFF);
   gpioTerminate();
}
