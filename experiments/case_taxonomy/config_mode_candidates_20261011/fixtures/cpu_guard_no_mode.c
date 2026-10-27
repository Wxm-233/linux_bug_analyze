/* Synthetic lexical contrast, not a historical normal commit. */
void trace_cpu_attribute(void)
{
	unsigned trace_tag;
	if (IS_ENABLED(CONFIG_CPU_BIG_ENDIAN)) {
		trace_tag = 1;
	} else {
		trace_tag = 0;
	}
	log_attribute(trace_tag);
}
