# Bambu 项目适配工具

Bambu Studio 工程准备、离线切片和产物核验直接用包内 [bambu_project.py](../scripts/bambu_project.py)。依赖 Python 3.10+ 标准库。`open` 可启动软件，适配器不接管桌面或发送打印。因个别步骤需鼠标键盘而转用 Computer Use 时，先取得[对应范围的接管同意](slicing-automation.md#单步回退与返回适配器)。[逐项验收](bambu.md#成果验收与阶段交接)和原生预览仍须完成。

## 在用户项目运行命令

从存放本轮工程的用户项目目录执行。例如在 PowerShell 中定位本次使用的技能，然后用实际文件替换 `source.3mf`：

~~~powershell
$skillDir = Join-Path $HOME '.agents/skills/wenchuang-master'
$adapter = (Resolve-Path -LiteralPath (Join-Path $skillDir 'scripts/bambu_project.py') -ErrorAction Stop).Path
python -B "$adapter" inspect --input "source.3mf" --report "inspect.json"
~~~

将 `$skillDir` 指向本次实际使用的技能目录。其他终端可用加引号的脚本绝对路径替换 `$adapter`。命令在用户项目内运行；工程、报告、运行目录和盘号须换成本轮实际值。报告写入新文件。

## 能力与适用范围

| 命令 | 行为 | 成功仍不代表 |
|---|---|---|
| inspect | 读取版本、参数、零件、盘、几何／路径校验值，生成可复查清单 | 软件已接受工程 |
| prepare | 定向修改已支持字段并维护预设修改记录，保留其他内容 | 已完成 GUI 回读或用户配置验收 |
| compare | 比较配置、对象、分盘与几何，列出差异 | 差异已获用户接受 |
| review | 只读已有 verification.json，按组索引或按编号查看一条原始问题，支持保留 issues 数组的旧报告 | 问题已解决或获准打印 |
| open | 用明确指定的 Bambu 可执行文件打开工程或查看副本 | 文件已加载、预览已检查或成果已验收 |
| slice | 绑定已验收工程，按当前程序能力在新目录离线切指定盘并检查产物 | 可发送打印；无问题也只是待预览 |
| preview | 从受支持的切片工程制作独立的仅供查看副本，验证 G-code 不变 | 正式发送包 |

Windows 下，同一份 02.08.02.61 单盘工程已分别用 02.08.02.61 和 02.09.01.70 实际切出 G-code。02.09.01.70 为基准版本。其他版本或跨版本工程按兼容试切处理，助手核对本机能力，并在已确认工程的副本上验证目标盘。`prepare` 直接改写 3MF 和 `preview` 重组查看包仍只处理已核实的版本与结构；遇到新格式，由助手只对受阻步骤按[单步回退](slicing-automation.md#单步回退与返回适配器)处理，不伪造版本标识。[跨版本操作顺序](slicing-automation.md#1-先核实本机能力与版本)

支持修改已存在且分组已核实的常用全局工艺／耗材／打印机参数、已识别项目字段和唯一对象级 metadata；支持范围由脚本字段表及实际版本验证限定，不因源文件有某字段就自动支持修改。对全局参数自动维护 different_settings_to_system（预设修改记录）：按“工艺、各耗材槽、打印机”合并实际变化键，保留原标记，多耗材只标记变化槽。缺标记且槽位可明确时允许补建，但必须做完整 GUI 另存回读；畸形分组、不能判定槽位或未知字段不猜测，回退原生设置。除这一经过核实的派生记录外，不支持新增任意字段、逐面绘制、修改器参数、换网格、重新分盘或自动定向。这些内容保留原样，超出范围使用原生工具。首次接入新结构、字段或特殊对象时先做隔离验证。

## 按摘要定位明细

在项目目录保存完整报告。默认把命令的单行 JSON 摘要返回对话。按当前任务提取必要的值，例如用 inspect 报告中的 plates 按实际 id 找目标盘、用 global_settings 按键读取本轮材料；完整配置、G-code 和运行日志留在本地。摘要中的选中盘、几何不确定标志、GUI 回读原因或问题计数都是下一步读取线索。

compare 按类别和字段定位差异。slice 有待复核项时直接返回 issue_index，按风险类别、问题种类、字段族与有依据的盘号分组。每组给出数量、原始编号范围和示例路径。plate 为 null 的项目级或未定位问题仍需判读；/plates/N 中的 N 是数组位置，只有核对输入与输出的实际盘号后才能归盘。配置阻断项另列字段和前后值，保留字段缺失标记。过长的值按 read_from_issue 提示展开。

先看随切片返回的索引。需要追溯某项时，按[项目目录与脚本路径](#在用户项目运行命令)运行适配器，按同一份报告中从 1 开始的 issues 编号提取原始记录。例如：

~~~text
python -B "$adapter" review --input slice-plate-01/verification.json --issue 3
~~~

旧报告只有原始 issues 时，省略 --issue 即可生成索引。首次摘要限制为 24 组、24 条配置变更及每组 12 段编号；有省略时另列数量，按需用 --all 查看全部组、路径和编号范围。编号只对当前报告有效。观察项仍在 observations 中。分组只用于定位，共用一组的问题可能成因不同。需要放行的配置、路径及未知问题逐一解释或引用确能覆盖相应范围的证据；未解决项保留待处理。实际预览、成果验收和发送授权保持独立。

## 使用顺序与确认边界

所有输出位于用户项目，不能写入技能目录。先按[在用户项目运行命令](#在用户项目运行命令)定位适配器。示例中的工程、软件路径和工艺值按本轮实际情况填写。

### 检查盘与零件

现有 3MF 先用上面的 `inspect` 按内容判定 `file_role`，读取版本、校验值、盘号及几何检查范围；同一输入已有本轮清单时直接复用。单独的 STL 等模型先转成可编辑工程。`sliced_toolpath` 和 `preview_copy` 只能查看路径；改参数须回到对应的可编辑工程。

### 准备参数变更

依据已确认的配置任务创建变更 JSON，参考 [格式示例](../assets/bambu-changes.example.json)。每项必须有 scope、key、from、to；对象项还需唯一 name，必要时带 id。from 必须匹配实际旧值；保持原类型和列表长度。示例对象名及数值仅演示格式，须替换。材料数组按材料编号明确修改，不能把缺项补成默认值。

~~~text
python -B "$adapter" prepare --input source.3mf --changes changes.json --output configured.3mf --report prepare.json
~~~

prepare 不切片。已有 G-code 的工程、模糊对象、未知字段、错误类型和不支持结构均拒绝；输出及报告不得覆盖已有文件。需要新一轮修改时新建版本，不能自动清理旧结果。

### 打开工程与回读

先用 inspect 的 file_role 核对用途。supported_for_mutation 指示该工程能否按已验证格式直接改写。跨版本切片还需核对可执行文件、工程来源及本轮产物。inspect --report 的 preview_marker 单独保留查看副本标记，原生纯路径文件通常无此标记。editable_project 可作为工程打开；mixed_project 同时含可编辑模型和已有路径，也可作为工程打开，但须核对保留的盘和零件是否覆盖本轮完整交付范围。作为项目打开后，在「准备」页确认实际模型可选中、盘号及材料／逐件设置可编辑。普通几何 3MF 需要导入并保存为 Bambu 工程；unverified 需用原生软件核实。open 只提出启动请求，不能当作已经核对。prepare 报告的 preset_override_retention 列出自动补记；gui_validation 说明实际载入必检、当前完整回读原因及条件，不代表已完成验证或用户接受。

首次接入版本／字段／结构、新建覆盖标记、软件忽略／重置参数或发现未知差异时，完整执行“原生另存 → compare → inspect”；同条件方法已验证的普通轮次，核对实际载入和本轮自动差异即可，不机械重复整套另存回读。下面的 compare／inspect 示例仅用于触发完整回读的轮次：

~~~text
python -B "$adapter" open --bambu "<实际可执行文件>" --mode project --input configured.3mf
python -B "$adapter" compare --before configured.3mf --after gui-saved.3mf --report roundtrip.json
python -B "$adapter" inspect --input gui-saved.3mf --report accepted-input.json
~~~

未触发另存回读时，使用实际载入并获接受的 configured.3mf 作为切片输入；触发回读则使用核对后获接受的 gui-saved.3mf。绑定所选文件的实际 SHA-256，不混用另一版。

展示结果并取得用户对当前配置版本的明确接受后，才进入切片。compare 保留全部发现的差异，由助手判断是否为可解释的元数据变化；差异退出码不应通过删除字段或忽略所有差异来消除；解释差异后在当前成果记录处置，不为取得零差异无限重跑。

### 对已选盘执行切片

使用已接受文件的 SHA-256，明确选择某一盘或 all。切片会将该次读取的原始字节写入独立快照，实际使用快照，避免确认后源路径变化而切到另一版本。

其他 Windows 版本沿用下面的 `slice` 命令。输入须为已验收的可编辑工程，几何可核验、无旧路径，工程版本与文件内原生 Application 标识一致；可以试读其他版本保存的工程。助手核对本机帮助中的 `--arrange`、`--slice`、`--export-3mf` 和 `--outputdir`；帮助空白时可从已授权的一个代表盘试切。可执行程序或工程版本偏离基准时，生成的结果标为 `needs_review`。由助手核对盘、参数、G-code 和实际预览，再交用户验收。

~~~text
python -B "$adapter" slice --bambu "<实际可执行文件>" --input gui-saved.3mf --accepted-sha256 "<该文件已核对的SHA256>" --plates 1 --run-dir slice-plate-01
~~~

示例中的 1 应换成本轮实际盘号。--plates 必填；all 表示明确选择全部盘，其他值为单个现存盘号。逐盘交付 G-code 时，各次调用使用同一份已验收工程作为输入，指定一个目标盘号和一个新的运行目录；这些目录保存各盘的运行产物。使用 all 时须已确认本轮需要全部盘。若实际输出只有一个多盘包，用同一工程按需逐盘调用适配器；若只能从原生界面逐盘导出，按[单步回退](slicing-automation.md#单步回退与返回适配器)处理并核对正式 G-code。--accepted-sha256 是调用者关于已接受版本的声明，只绑定文件内容，不能证明用户实际确认；助手不得自动计算后填入来跳过验收。开发验证使用已授权的隔离测试范围，不能生成虚假的产品验收记录。

每次 run-dir 必须全新，已有空目录也拒绝。工具不自动摆盘／定向，临时目录、stdout、stderr、输入快照、run.json、verification.json 和实际输出保留在本次目录。--timeout 默认 600 秒；超时记录 PID 和可能仍运行状态，不自动重试或终止其他 Bambu 实例。先核对该进程及已有产物，再决定后续操作；已存在的运行目录不重用。

### 处理切片差异

`slice` 已比较输入快照与输出，复用同次 `verification.json`。若 3MF 来自 GUI 或外部脚本，先用 `inspect` 识别新产物，再用 `compare --before "<已验收工程.3mf>" --after "<实际产物.3mf>"` 核对双方可取得的字段；需要留存明细时加 `--report` 和新的报告路径。退出码 3 表示发现差异，逐项判读。纯切片包不含可编辑几何，缺模型等角色差异不能证明参数漂移；核对可比参数、盘号与 G-code，缺失证据标未验证。裸 `.gcode` 不传给 3MF 命令，按盘核对其来源、路径和可取得的配置。

对适配器生成的切片，按[摘要定位规则](#按摘要定位明细)读取 issues／observations。`needs_review` 表示需要判读。`verification_schema=2` 记录 category、affected_stages、recommended_action 及 `automatic_reslice=false`。保留原始差异与警告。

| 分类 | 处理重点 |
|---|---|
| configuration_blocker / path_integrity_blocker | 查明参数漂移、缺盘、路径或校验问题，修正原因后决定是否需重切；未解决不接受／发送 |
| send_metadata_gap | 核对正式交接所需设备／材料／盘资料，缺口阻止发送，但不据此断言几何路径错误 |
| auxiliary_statistic | 交叉核对可用估算或标未知，不仅为清除异常统计反复切片 |
| unknown_difference / slicer_warning / unknown_issue | 保留原始差异／警告，定位实际影响后决定处理；未知不等于可忽略 |
| expected_derived_output | 保存正常派生变化，其他路径与参数检查继续适用 |

同次运行复用与输入快照 SHA 绑定的清单，输出只解析一次后比较；不存在跨项目或忽略文件变化的缓存。按 [切片检查](bambu.md#切片检查) 集中查看首层及适用风险区，满足结束条件即提交成果验收。已知 filament_prime_volume 归一化与设备／首层时间元数据问题仍只检测和报告，不声称修改预设记录就修好了这些独立问题。

### 打开已有路径预览

sliced_toolpath 是无可编辑模型的原生纯切片包，preview_copy 是适配器生成的仅查看副本，两者都可走 open --mode preview。回「准备」页改耗材请打开同盘对应的可编辑工程。核实实际路径与来源版本后再决定交付用途；启动预览本身不构成发送授权。需要直接查看 CLI 原路径时：

~~~text
python -B "$adapter" preview --input slice-plate-01/output/sliced.3mf --output view-only.gcode.3mf --report preview.json
python -B "$adapter" open --bambu "<实际可执行文件>" --mode preview --input view-only.gcode.3mf
~~~

preview 保留原始产物，添加仅供查看标记；slice 会拒绝将这种副本作为输入。新包每份 G-code 必须与原产物一致，未知引用／结构拒绝转换。当前转换要求保留的每盘都有对应 G-code；单盘切片后仍含其他未切片盘时会拒绝，由助手改走当前软件的原生查看入口，保留已授权的盘范围。按 [实际预览规则](slicing-automation.md#42-区分工程打开与已有路径预览) 检查是否真正读取对应路径，自动重切必须另记结果。查看副本不可发送打印；正式文件及物理授权继续按原流程核验。

## 退出码与成果状态

- 0：当前命令技术步骤完成。slice 的最好状态仍是 generated_pending_preview，不代表已验收或可打印。
- review 能读取索引或指定问题即返回 0；可从索引的 issue_count 判断是否仍有待处理项。它只读取现有报告，不重新切片。
- 2：输入、格式、版本、路径、问题编号或文件保护检查阻止操作；先读错误。
- 3：compare 有差异，或 slice 已产生结果但需要处理检查项；保留报告，不能当作普通成功忽略。
- 4：切片启动失败、进程失败或超时；查 run.json 和日志，不盲目重跑。

## 验证与开源发布

包内 [核心测试](../scripts/tests/test_bambu_3mf.py) 和 [命令行测试](../scripts/tests/test_bambu_project.py) 使用合成小型工程与假进程验证文件保护、格式、版本、确认绑定、盘范围、参数保留标记、问题分类、同轮解析复用、参数差异及预览内容，不启动真实设备。从上文同一项目目录运行：

~~~text
python -B -m unittest discover -s (Join-Path $skillDir "scripts/tests") -v
~~~

测试产物与缓存应指定到使用者允许的临时目录。公开包只包含原创脚本、格式示例和通用方法，不包含作者个人工程、路径、日志或凭据。单元测试不能代替当前机器的软件打开、切片和 GUI 预览验证；适配器版本变化后按影响范围补验。
