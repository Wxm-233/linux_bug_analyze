# 判据修订1：M1中“架构自己的版本”包括drivers/acpi下的架构目录（任何模型调用之前写定）

试列M1检查点时发现，`cpc_read_ffh`等默认实现，RISC-V的版本在`drivers/acpi/riscv/`而不在`arch/riscv/`，会被误当作“RISC-V没有提供自己的版本”。因此M1判断“某架构提供了自己的版本”时，除该架构的`arch/`目录外，也看`drivers/acpi/<架构>/`下的`.c`文件。其余不变。
