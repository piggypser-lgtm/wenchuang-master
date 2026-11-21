# 有明确许可与实物记录的机构卡片

核查日期：2026-11-13（新增 M15；其余沿用各卡证据日期）。现有 **15 张具体方案卡**；相同函数的尺寸变体合并，不把方案卡数量当作不同机械原理数量。共同选择与验证规则见 [成熟机构复用](mechanism-reuse.md)。按动作选卡，再读对应来源，无需全部展开。

本批证据来自作者／复现者实打文字或实物照片；未由本 skill 维护者试打，不包含量化承载或循环寿命合格结论。许可证按作者固定版本的声明记录；第三方模型保持原许可及署名，本包 MIT 只覆盖原创归纳。固定提交是本次核查版本，不表示历史照片或试打必然使用同一提交。用途扩展和下列改造建议属于设计判断。

| 卡号 | 具体方案／适用动作 | 许可 | 已核对的物理证据 | 件数边界 |
|---|---|---|---|---|
| M01 | BOSL2 原位打印单轴铰链：开合、翻折 | BSD 2-Clause，限定本卡函数 | 作者记录指定示例成功打印、设备及层高 | 2 个运动构件，0 外购件 |
| M02 | BOSL2 双耳弹性卡扣：插入固定、按耳释放 | BSD 2-Clause，限定本卡函数 | 作者 PLA 配合试验及拆卸表现 | 单扣／插座所在构件共 2 件，0 外购件 |
| M03 | Mini Clamp：外框弹簧夹 | CC BY 4.0 | 实打照片、夹住铅笔的状态及作者使用说明 | 0 外购件；独立打印实体数待源模型核对 |
| M04 | Hinged Case：两件式挤压开盖扣合盒 | CC BY 4.0 | 实物装物照片、作者打印条件与材料说明 | 2 打印件，0 外购件 |
| M05 | Flexi Rex 加强链节：串联活动、弯曲 | CC BY-SA 4.0 | 作者实打站立照片、材料与活动说明 | 按取用链节／连接实体计数，0 外购件 |
| M06 | Mix 'n Match Twisty Fidget：磁吸旋转、段落触感 | CC BY 4.0，仅模型 | 作者打印成品照片与装配说明 | 打印件／磁铁随变体核对，含嵌件工序 |
| M07 | Planetary Gear Coaster：行星齿轮转动 | CC BY-SA 4.0 | 作者成品照片、ABS 打印及装配记录 | 6 打印件；加外齿圈为 7 件，0 外购件 |
| M08 | Linkage Construction Kit：连杆与手摇动作组合 | CC BY 4.0，仅通用套件模型 | 作者打印连杆、底板和剪式装配照片 | 按选用组合计件；打印销或按需标准紧固件 |
| M09 | Customizable Universal Latch：旋转搭扣 | CC BY 4.0 | 作者组装实拍、默认尺寸使用经验 | 4 打印件；安装胶水／紧固件另计 |
| M10 | Zig-zag Leaf Spring：弹性摆动与回弹 | CC BY-SA 4.0 | 作者独立弹簧试印及把玩记录 | 独立叶簧 1 打印件；两端适配件另计 |
| M11 | Bistable Auxetic：平展／穹顶形变 | GPL-3.0 源码 | 作者两状态打印实拍；无循环数据 | 1 连续 TPU 结构；外部连接件另计 |
| M12 | Sturdy Infinity Cube：连续铰接翻折 | SCAD 为 MIT；作者平台 STL 为 CC BY 4.0 | 作者不同尺寸与折叠状态实拍；SCAD 已读取 | 8 块体及 8 连接模块位置，独立实体接收后核对；含牺牲薄条 |
| M13 | Keyswitch Tester：现成机械键轴的按压安装接口 | 主源及已查依赖为 MIT | 作者实装照片、P1S／PLA 配合试用记录 | 1 打印座＋实际键轴数量，键帽另计；主题改作件数另核 |
| M14 | Nested Rings：双锥面轴向滑移／收合、翻转 | CC BY 4.0 | 复现者 PLA 制作自述；照片／动作未目视核验，具体变体与版本未对应 | 默认源码六个运动环，0 外购件；按实际参数重计 |
| M15 | Collapsibasket：套层升降、转位保持 | 主源及两项依赖 MIT，所用 BOSL 文件 BSD 2-Clause | 作者制作／功能自述；本机最小依赖输出与原 STL 几何一致，未试打 | 默认 5 个运动构件，0 外购件 |

M06–M15 的完整卡片见 [文创与玩具的互动机构](toy-mechanisms.md)。M06、M08 的设计源由作者在定制说明中明确提供，但本次尚未取回，采用前须核对实际文件与许可；M07 已读取固定版本设计源。收录为候选不表示全部源文件已在本机运行通过。

原位打印的运动实体分别计件；附加装饰、安装块和紧固件按最终方案追加。静态照片不证明动作全程、保持力或寿命；这些证据边界在各卡继续细分。

## M01 — BOSL2 原位打印单轴铰链

- **动作与用途：** `knuckle_hinge(in_place=true)` 的互锁铰链，可评估轻载盒盖、翻折文创；2 个相对运动构件，无另装销轴。
- **来源与许可：** BOSL2 v2.0.784，提交 `35262999f4ca32715fdb7ac51fc9cf804a67b0a9`；[固定源码及示例 17、18](https://github.com/BelfrySCAD/BOSL2/blob/35262999f4ca32715fdb7ac51fc9cf804a67b0a9/hinges.scad#L288)、[BSD 2-Clause](https://github.com/BelfrySCAD/BOSL2/blob/35262999f4ca32715fdb7ac51fc9cf804a67b0a9/LICENSE)。采用时保留对应版权声明。
- **实物证据与条件：** 上述源码注释明确记录 Prusa MK3S 打印成功。示例 17 为 2 mm 铰链筒、25 mm 长、11 节，0.15 mm 层高，`gap=0.15`、`clearance=0.15`；示例 18 为 4 mm 厚、25 mm 长、13 节，0.2 mm 层高、`gap=0.2`。按源示例排向；示例 18 的展示参数 `ang=35` 必须改为 `ang=0` 才是作者规定的打印姿态。材料、喷嘴及耐久未给出。
- **保护与适配：** 保留互锁锥面、段间隙、轴线与叶片关系、根部及闭合净空。外围叶片可接外观或安装面，不能堵塞运动间隙。
- **本次验证重点：** 查全角度干涉、根部及支撑清理；原材料等缺项影响配合时补局部转动／防脱试样。增加力臂、缩放或改间隙后不继承原成功结论。作者打印成功不等于承重铰链合格。

## M02 — BOSL2 双耳弹性卡扣

- **动作与用途：** `rabbit_clip()` 单扣和插座用于固定连接，适合可拆壳体或拼接；不是按一下锁定、再按一下释放的 push-push 机构。两侧所在构件共 2 打印件，0 外购件；融入已有壳体不必新增独立连接件。
- **来源与许可：** 同 M01 的固定提交；[源码示例 1及实物说明](https://github.com/BelfrySCAD/BOSL2/blob/35262999f4ca32715fdb7ac51fc9cf804a67b0a9/joiners.scad#L1122)、[BSD 2-Clause](https://github.com/BelfrySCAD/BOSL2/blob/35262999f4ca32715fdb7ac51fc9cf804a67b0a9/LICENSE)。该结论不覆盖库中全部函数；例如同文件 `snap_pin()` 另有 CC BY-SA 来源说明，不能套用本卡许可。
- **实物证据与条件：** 作者记录 PLA、Prusa MK3 下多组尺寸可用。默认 `clearance=0.1`、`depth=5`；可从 6×7 mm、`snap=0.25`、弹性线厚 0.8 mm、`compression=0.1` 的示例组开始查原文。另有很难拆或 `lock=true` 不可逆组，需维护时不默认选用。层高、喷嘴、保持力及寿命未知。
- **保护与适配：** 保留双耳曲线、梁厚、扣齿、预压、根部与退出通道；外围安装块可改。示例试验座为穿通开口，不能把封闭插座或双头中间卡扣当作相同试验拓扑。
- **本次验证重点：** 先区分可拆与永久固定要求；外围适配查插拔路径和根部。改变梁、材料、层向、插座封闭方式或拆卸要求时，补相应插拔／保持／释放试样，不把“很紧”直接当作合格。

## M03 — 外框弹簧夹 Mini Clamp Print-in-place

- **动作与用途：** 外框兼作弹簧的原位打印夹具，可评估便签、轻小物件或线材夹持；无外购弹簧、无需装配。作者未写独立运动实体数，接收源模型时核对，不能因一次打印记作 1 件。
- **来源与许可：** DrLex，提交 `f859480927bd6f6477e239ef1f711df95b55f904`；[可编辑 Blender 源](https://github.com/DrLex0/print3d-mini-clamp/blob/f859480927bd6f6477e239ef1f711df95b55f904/MiniClamp-PrintInPlace.blend)、[CC BY 4.0](https://github.com/DrLex0/print3d-mini-clamp/blob/f859480927bd6f6477e239ef1f711df95b55f904/LICENSE.md)、[作者说明](https://github.com/DrLex0/print3d-mini-clamp/blob/f859480927bd6f6477e239ef1f711df95b55f904/README.md)。保留作者及其注明的 [muzz64 Germz 灵感来源](https://www.thingiverse.com/thing:3495390)。
- **实物证据：** [打印成品照片](https://github.com/DrLex0/print3d-mini-clamp/blob/f859480927bd6f6477e239ef1f711df95b55f904/images/photo1.jpg)、[夹住铅笔的实拍](https://github.com/DrLex0/print3d-mini-clamp/blob/f859480927bd6f6477e239ef1f711df95b55f904/images/photo3.jpg)。能支持该状态下的夹持，不证明额定夹力或长期保持。
- **原条件与缺项：** 作者推荐 PETG；0.4 mm 挤出线宽配 4 圈，或 0.6 mm 线宽配 3 圈，作者使用 15% 填充；线宽不能抄成喷嘴直径。提供 `xtraTol` 大间隙变体。设备、层高与循环寿命未给出，PLA 长期受力表现不能由 PETG 建议外推。
- **保护与适配／验证：** 保留弹性外框截面、夹爪根部、活动间隙。改夹持面时检查实际物体与开口范围；改框、材料、缩放或新增长期夹持要求时，验证相应回弹、夹持和保持。不能在弹性框外包一层装饰后声称只改了外观。

## M04 — 两件式挤压开盖扣合盒

- **动作与用途：** DrLex 的 Hinged Case for Earphones，2 打印件、0 外购件。卡入式铰链配合壳侧挤压辅助抬盖，适合轻小收纳盒；不是 push-push，也不是自动弹出盒盖。
- **来源与许可：** 提交 `069e55b18373d08604bb2533ffe3a53ed7a460f9`；[可编辑 Blender 源](https://github.com/DrLex0/print3D-hinged-earphones-case/blob/069e55b18373d08604bb2533ffe3a53ed7a460f9/Hinged_Case_for_Earphones.blend)、[CC BY 4.0](https://github.com/DrLex0/print3D-hinged-earphones-case/blob/069e55b18373d08604bb2533ffe3a53ed7a460f9/LICENSE.md)、[作者说明](https://github.com/DrLex0/print3D-hinged-earphones-case/blob/069e55b18373d08604bb2533ffe3a53ed7a460f9/README.md)。保留 DrLex 及 [yyh1002 原模型](https://www.thingiverse.com/thing:2548489) 署名。
- **实物证据与条件：** [装入耳机的实物照片](https://github.com/DrLex0/print3D-hinged-earphones-case/blob/069e55b18373d08604bb2533ffe3a53ed7a460f9/images/case1.jpg)，作者说明 PLA、PETG 均可用，实打设置为 0.2 mm 层高、25% 填充、3 圈、无支撑／raft。`opening.jpg` 为渲染示意，不计实物证据。喷嘴、量化锁紧力和寿命未核实。
- **保护与适配／验证：** 保留销座、扣合、侧壁弹性及手指按压区。改内胆或外形查开合、物体取放与装配；加厚、包覆或增加筋会影响挤压释放，须验证受影响的开盖功能。原文修配方法不作为默认加工步骤，优先准确打印或在许可范围内调整设计。

## M05 — Flexi Rex 加强串联活动链节

- **动作与用途：** 复用加强链环用于分节文创和非承重活动挂件；原位打印多实体，按实际取用链节及连接实体计数，0 外购件。不是承载链条或精密定位关节。
- **来源与许可：** DrLex，提交 `ef49d3e0b149486c25972124154b6c3824532053`；[可编辑 Blender 源](https://github.com/DrLex0/print3D-FlexiRex/blob/ef49d3e0b149486c25972124154b6c3824532053/Flexi-Rex-improved.blend)、[CC BY-SA 4.0](https://github.com/DrLex0/print3D-FlexiRex/blob/ef49d3e0b149486c25972124154b6c3824532053/LICENSE.md)、[作者说明及 Hinge Design](https://github.com/DrLex0/print3D-FlexiRex/blob/ef49d3e0b149486c25972124154b6c3824532053/README.md)。沿作者列明的 [airfish](https://www.thingiverse.com/thing:2189652)、[Kirbs](https://www.thingiverse.com/thing:1759297)、[zheng3](https://www.thingiverse.com/thing:929413) 保留来源；分发衍生内容遵守原 ShareAlike 条件，不改标 MIT。
- **实物证据与条件：** [实打站立照片](https://github.com/DrLex0/print3D-FlexiRex/blob/ef49d3e0b149486c25972124154b6c3824532053/images/rex-imp1.jpg)，作者标注 rigid.ink silver ABS，并说明脱板后应能活动。原尺寸推荐 0.4 mm 线宽、0.2 mm 层高、3 圈、15% 填充、5 顶／4 底，无支撑／raft。推荐值与照片条件分别记录，没有量化负载或耐久数据。
- **保护与适配／验证：** [作者尺寸示意](https://github.com/DrLex0/print3D-FlexiRex/blob/ef49d3e0b149486c25972124154b6c3824532053/images/Hinge_dimensions.png) 供核对链节，不以图片量尺替代源几何。保留轴孔周围、链环端部截面、间隙和运动空间；改外观后查质量、平衡及根部载荷。缩放、换材或改变链节排列后验证受影响的活动、防脱和打印间隙。

## 当前缺口及使用边界

这 15 张卡覆盖开合、固定连接、夹持、串联活动、磁吸旋转、齿轮、连杆、搭扣、弹性回位、形态切换、连续翻折、外购键轴的按压安装接口、嵌套环轴向滑移／翻转及套层容器升降／转位保持；套件不等于其全部新组合已验证，也不等于 15 种独立机械原理。[待查记录](mechanism-candidates.md) 分别保留按压、形变、定位及行走等候选的证据缺口，其中 W13–W15 仍跟踪套层伸缩与剪叉抓手，W16 已转为 M15，不重复计数；同向两态按压及其他长行程／定位滑动方案仍有证据缺口。M14 只支持其嵌套环玩法与所列证据，不能替代任意直线导轨；M13 的瞬时回弹也不能替代按压锁止。STEMFIE 按[资料索引 R17](resource-library.md#r17-stemfie可打印机械零件源库)作为零件来源库，不以其零件或尺寸变体数量增加机构卡数。普通入口仍见 [EDC 参考](fidget-edc.md)和[参数化结构](parametric-structures.md)。

作者发布的许可及列明来源已记录，不宣称所有上游权属已独立审计。采用时若发现实际文件许可与卡片冲突，停止复用该候选并说明替代；不把未知许可当默认许可。不自动安装库、运行下载代码或发送打印；创建模型、安装、上传和试打沿用原阶段与授权边界。
