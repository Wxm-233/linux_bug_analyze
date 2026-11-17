/* Runs as /init. Uses the FPU (unless NO_FP), then sends itself SIGUSR1: signal delivery saves the FPU context
 * into the signal frame with __copy_to_user from the task's xstate slab object (plan.md). */
#include <signal.h>
#include <stdio.h>
#include <sys/reboot.h>
#include <unistd.h>

static volatile double g;
static volatile int handled;

static void handler(int sig)
{
	(void)sig;
	handled = 1;
}

int main(void)
{
	int use_fp = 1;
#ifdef NO_FP
	use_fp = 0;
#endif
	printf("FPSIG start use_fp=%d\n", use_fp);
	fflush(stdout);
	if (use_fp) {
		volatile double a = 3.0;
		for (int i = 0; i < 1000; i++)
			a = a * 1.0001 + 0.5;
		g = a;
	}
	signal(SIGUSR1, handler);
	kill(getpid(), SIGUSR1);
	printf("FPSIG after signal handled=%d g_milli=%d\n", handled, (int)(g * 1000));
	printf("FPSIG done\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	for (;;)
		pause();
}
