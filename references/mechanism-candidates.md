# 互动机构待查记录

维护日期：2026-11-13（W15 补核来源及流程授权范围；W16 已升为 M15，既有条目沿用各自证据日期）。现有 W01–W15 共十五项待查；W16 仅保留升卡跳转。仅在当前用途确实相关时读取对应项；待查记录不计入[正式机构卡](mechanism-library.md)。准入及采用规则见[成熟机构复用](mechanism-reuse.md)。

## W01–W04：按压、切换、卷带与软弹


以下四项的动作、作者许可与实物记录已继续核查，但未获得一手的具体可编辑设计源清单。官网通用许可段出现 STL／STEP／F3D，不等于实际提供所有格式。本轮重新读取作者官网和公开文件索引，仍未取回设计源；W04 已定位精确官方 STEP 下载地址，状态见该项。不能据聚合索引的格式标签补齐证据；这些候选可用于共创解释玩法，采用前须补源文件核对，不作为已完成取证的成熟核心。

### W01 — Super Clicky 同向两态按压，优先补核

- [作者项目 11](https://3dprinty.xyz/project/11)、[原版发布页](https://thangs.com/designer/3DPrinty/3d-model/Super%20Clicky%20Fidget%20Button-22376)、[Double Clearance 发布页](https://thangs.com/designer/3DPrinty/3d-model/Super%20Clicky%20Fidget%20Button%20-%20Double%20Clearance-53800) 均指向类似圆珠笔的两态按压用途，作者声明模型 CC BY 4.0；[作者演示](https://youtu.be/bJq6pNM4eR8)。双间隙页另有复现者报告制作 3 个并可使用，属于第三方自述，不是本项目测试。
- 双间隙页的约 15 mm 长、5 mm 直径弹簧为作者该版本经验值，不包含完整刚度／预压规格；可选 M3 螺杆输出动作。实际打印件数、行程和承载须从具体源文件与应用确认。优先采购合适的标准成品弹簧，不默认剪弹簧或热加工线材。
- **本轮补核：** 作者 Updated 页指向 [Printables 143740](https://www.printables.com/model/143740)和 [Thingiverse 4945227](https://www.thingiverse.com/thing:4945227)，另将 4879008 标作原始紧间隙版。公开次级索引在 143740 下仅列 STL，不能反推所有版本没有 CAD；文件数也不等于装配件数。
- **未解决：** 实际 STEP／F3D 文件名、内容、许可对应及版本。当前官网 Updated、原版和双间隙版不得当成同一文件；官网与双间隙页的凸轮／按钮层高建议也不一致，不能拼成预设。采用前补实际文件清单并选择确定版本。
- **适配边界：** 可探索角色局部伸缩或状态切换；作者的点击体验不能直接证明弹出新负载。取得设计源后优先保护凸轮、导向、止挡、弹簧座和预压关系，再按新增行程、重量与保持要求验证。

### W02 — Super Toggly 双按钮／翻转切换

[作者项目 14](https://3dprinty.xyz/project/14) 为 CC BY 4.0，已有目视核对的成品和开壳机构照片，另有 [作者演示](https://youtu.be/zfiyeE8l3-0)。默认使用打印弹簧、无需外购硬件，作者要求弹簧满填充且走线沿其长度；实际件数随普通版、加强件或表情按钮变化。适合表情或左右状态切换，**不是同一按钮连续按压的 push-push**。具体 CAD 文件仍未取得；本轮作者官网的 Customization 仅介绍零件变体，没有明确提供设计源。[Printables 143072](https://www.printables.com/model/143072)的次级索引仅列 STL，也不能据此确认作者从未提供 CAD。补核后保护弹簧、接触面、支点及限位，外观变体不能侵占弹性空间。

### W03 — Shutter 卷带滑动

[作者项目 82](https://3dprinty.xyz/project/82) 与 [定制版发布页](https://thangs.com/designer/3DPrinty/3d-model/Customizable%20Shutter%20Fidget%20%26%20New%20shutters-914592) 声明 CC BY 4.0；已查看作者实物照片，定制版有 [制作教程](https://youtu.be/W6o0j-xrIEU)，尚未确认实际 STEP／F3D 清单。本轮定制页只读到 Fusion360 标签、教程入口和通用许可段；“用 Fusion 制作教程”不等于“公开 Fusion 源”。基础版 [Printables 534358](https://www.printables.com/model/534358)与定制版分别核对，不用基础版的文件索引推断定制版内容。上框、下框、卷带是三个功能组件，不直接等于三个独立运动实体；作者建议 PETG 卷带、无支撑打印。可探索鳞片、条纹或背部触觉滑动；补核后保护柔性连接、厚度／节距、弯曲半径与导向空间，不自动把解压卷带当成承重或密闭盒盖。

### W04 — Pop Fidget 弹性按压系列

[基础版 99](https://3dprinty.xyz/project/99)、[圆形 106](https://3dprinty.xyz/project/106)、[钥匙扣 107](https://3dprinty.xyz/project/107) 均声明 CC BY 4.0；已查看 [作者实物照片](https://3dprinty.xyz/images/media/pop-fidget/1.png)，但具体可编辑设计源仍待核查，外形变体合并为一项。TPU 内件配刚性壳和压入按钮，可探索角色腹部／肉垫触感；作者推荐 92A TPU、95A 亦可，垫片至少 5 圈。单材料设备需预印内件并在壳体打印中暂停嵌入，不能称为纯 PLA 或全程无人干预。补核后保护弹性变形空间、按钮卡持和嵌件齐平关系；件数按所选按钮阵列统计。

**本轮获得的精确入口：** 作者基础版 99 指向 [Printables 731590](https://www.printables.com/model/731590)。[次级文件索引](https://3dfinder.io/model/printables/731590-pop-fidget-multi-material-design?lang=en)列出 `Template.step`，文件 ID `3268362`、索引大小 1,023,600 字节；其公开下载按钮返回 [Printables 官方 STEP 地址](https://files.printables.com/media/prints/731590/stls/5990189_cc3c52ea-a71f-4f12-8be5-729f13538ead_43bf6d40-6f9b-4050-a1fa-b9f9ddf6a520/template.step)。此前连接超时或工具无法读取；2026-11-08 再次公开只读下载返回 HTTP 403，实际文件仍未取回，不能把索引大小当实测大小，不能记录 CAD 校验值、实体数或完整设计源已核实。

下一次有可读取的官方文件或用户提供文件时，优先核对 STEP 内容、与基础版的对应及其覆盖的功能核心，再决定是否升卡；不要把该线索自动推广到圆形／钥匙扣版本。精确入口是后续补核线索，不保证永久有效，也不授权绕过下载限制。

## W05–W10：定位、开合、行走与棘轮

### W05 — Hirth 端面齿盘定位

[agentscad 源码](https://github.com/GillesBouissac/agentscad/blob/master/hirth-joint.scad)和[作者说明](https://github.com/GillesBouissac/agentscad/wiki/Hirth-Joint)可读，源文件头有允许修改与分发的自带授权，但不改称标准 BSD 许可证。两片对向齿盘还需轴与预紧件，可探索定位翅膀或调角支架。**待补：一手实物证据及完整依赖许可**；已将本轮主源码核查固定到提交 `f463cc4127489f33433c830afbf4ccce8af65afd`。实际调用的[skin.scad](https://github.com/openscad/list-comprehension-demos/blob/master/skin.scad)未见文件头授权；继续检查其仓库目录、README 与公开 issue 后，仍未补到许可，[scad-utils](https://github.com/openscad/scad-utils/blob/master/LICENSE)的 MIT 不能覆盖它。作者 [Hirth 教程](https://github.com/GillesBouissac/agentscad/wiki/Hirth-Joint)给出的是代码／预览示例；新定位的 [Thingiverse 3838407](https://www.thingiverse.com/thing:3838407)尚未读取到可核对的一手实拍，聚合页的成功使用转述不填补该缺口。不能将当前整套依赖称为授权已齐，采用前须补齐或选择获许可且有适用实物记录的替代实现。

### W06 — LoboCNC 四瓣虹膜盒

[原模型 1817180](https://www.thingiverse.com/thing:1817180)有[实际打印记录](https://www.youtube.com/watch?v=oLlPiXsoVfY)；[Frank Zhao 的第一手文章](https://eleccelerator.com/3d-printed-mechanical-iris-dome-all-one-piece/)说明他查看过原版 SolidWorks 特征树，但随后从零重建了自己的 Onshape 设计。文章中的新模型、参数可调性、打印条件和授权不能移用给 LoboCNC 原版；原文只增强了原版设计源曾提供的证据。**待补：原作者许可及实际源文件／版本**，转载 CC BY-SA 标签不代替原声明。[锁定变体](https://www.printables.com/model/257845-print-in-place-iris-box-locking)须单独核查。可探索花苞、眼睛或宝珠开合，原方案需剪断薄连接桥，不能写无需后处理；不默认额外剪切适合当前需求。

### W07 — Wobbly 重力斜坡行走

[cevinius 作者页](https://www.cevinius.com/wobbly/)有重力下坡行走说明和实物动作入口，指向[原模型 170932](https://www.thingiverse.com/thing:170932)。**待补：原始许可、123D Design 源的具体文件和当前可取得性**，两者仍只有转载线索。本轮补查作者网站的公开项目索引，未找到额外源文件或授权入口；这不是确认不存在源码，而是当前尚未取得。需要硬币配重和少量胶水，打印件数未核，旧格式转换能力也待核。可探索企鹅或鸭子散步，不表述成平地自驱或无外购件。

### W08 — Alex Matulich 参数化 Strandbeest

[具体制作文章](https://www.nablu.com/2020/05/building-strandbeest.html)的 Getting the strandbeest parts 段明确为本设计提供 OpenSCAD 源与 STL，并指向 [Printables 129102](https://www.printables.com/model/129102-parametric-strandbeest-in-openscad)及 [Thingiverse 4390692](https://www.thingiverse.com/thing:4390692)。这是针对本设计的一手源提供说明；实际文件仍未取回，不能记录虚构文件名、版本或校验值。文章含实物装配与运动限制，[第三方实际改造](https://core-electronics.com.au/projects/quad-beest-project/)进一步说明源文件被修改并试印。**待补：原作者用途／改编与分发许可及实际所选源版本**，“可修改”不等于开放全部用途；网页中的 `normalize.css` MIT 声明属于网站样式代码，不属于模型。第三方附件未取回，亦不能代替原作授权。每对腿 26 件另加框架／曲轴，卡扣式无需金属紧固件，但原记录需在地毯上拖动，不是已实现自重下坡或风力自走。只在多足玩法收益值得装配负担时考虑。

### W09 — SHR3D 一体棘轮挂件

[作者模型 85312](https://www.printables.com/model/85312-pendant-ratchet-for-bits-privesek-racna-na-bity)的[原始实拍](https://media.printables.com/media/prints/85312/images/907173_d6f1c72f-f61c-4691-9dad-761cc31d16ac/img_3854.jpg)已目视，打印件与作者铭牌同框；照片不证明连续棘轮动作或额定扭矩。**待补：实际 `racna.scad` 及原作者许可**，现有聚合页的文件表和 CC BY 标签仅作线索。继续核查未取得作者源文件或许可；[Sharkus 的同名源码设计](https://cults3d.com/en/3d-model/tool/mini-ratchet-for-bits-as-a-key-chain)另需笔弹簧并介绍胶粘方案，不能将其 `racna.scad` 文件或授权填到 SHR3D 卡。可探索方向受限拨轮和咔嗒挂件；工具用途还需批头，件数与安装按实际文件核对。

### W10 — PAMS 可锁紧万向关节

- **已核资料：** [作者仓库固定提交](https://github.com/makersmakingchange/Universal-Lockable-Joint/tree/88ca9de97d91fed0956c61a784a754393172eff7)有左右壳 STEP／SolidWorks、装配资料和已目视的[真实装配照](https://github.com/makersmakingchange/Universal-Lockable-Joint/blob/88ca9de97d91fed0956c61a784a754393172eff7/Photos/Joint_orange.png)；`adjustment.png` 是 CAD 示意，不算实拍。
- **本轮补到的许可：** 已实际读取 V5.00／December 2021 的[装配指南](https://github.com/makersmakingchange/Universal-Lockable-Joint/blob/88ca9de97d91fed0956c61a784a754393172eff7/Documentation/Universal_Lockable_Joint_Assembly_Guide.pdf)、[打印指南](https://github.com/makersmakingchange/Universal-Lockable-Joint/blob/88ca9de97d91fed0956c61a784a754393172eff7/Documentation/Universal_Lockable_Joint_3D_Print_Guide.pdf)和[变更记录](https://github.com/makersmakingchange/Universal-Lockable-Joint/blob/88ca9de97d91fed0956c61a784a754393172eff7/Documentation/Universal_Lockable_Joint_ChangeLog.pdf)，页脚均有作者署名及 **CC BY-SA 4.0**。这补齐项目文档许可；仓库仍无统一 LICENSE，不能自动扩展为全部 CAD／STL 的许可。
- **仍待补：** 设计文件适用许可与手柄 CAD。[issue 4](https://github.com/makersmakingchange/Universal-Lockable-Joint/issues/4)仍开放且未补文件，不能将壳体有 STEP 写成全套可编辑，也不能用文档许可替代缺失设计源。
- **采用边界：** 基本方案为左右壳与手柄共 3 打印件；大手柄是替换件，螺栓盖按需另计。需要 M10×70 螺栓、螺母、橡胶垫及应用中的 PVC 管；README 另列平垫，须对所选装配核对物料。打印指南总重量与逐件重量不一致，不照抄作成本依据。变更记录有旧版 PVC 套筒高载开裂及后续加厚、调整接触面角度的修订，不能把旧版失败或新版改进混为整个系列的统一表现；无量化承载、耐久结论。可探索调角支架，缩小或改变夹持对象仍按实际差异验证。

## W11–W12：新增按压与滑动线索

### W11 — MrStump 磁斥回弹按钮

[作者 Thangs 项目](https://thangs.com/designer/mrstump/3d-model/Fidget%20Button%3A%20Magnetic%20and%20Customizable-948392)明确介绍 OpenSCAD／Customizer，并亲述 8×1 mm 磁铁和胶粘装配。动作是磁斥瞬时回弹，不是同向两态锁止。**待补：原始许可、实际 SCAD 文件及版本、物理证据对应**；[原 Thingiverse 6272414](https://www.thingiverse.com/thing:6272414)当前未能读取，不能从“可定制”推断允许全部改作或商用，照片入口未目视核对。取得证据后保护磁铁座、极性、导向、防脱与行程，改外壳时核对偏心按压；磁铁尺寸只是作者案例，不作为通用采购值。

### W12 — Cheddah / Lncendos 嵌套多边形滑动

[作者本人说明](https://www.reddit.com/r/3Dprinting/comments/1q21iim/i_made_a_fully_customizable_polygon_fidget_in/)明确提供参数化 FreeCAD 主工程并声明 General Public License，指向[原模型 1537410](https://www.printables.com/model/1537410-polygon-fidgets-fully-customizable-trianglesquarep)。已目视[作者原始实拍](https://i.redd.it/c6iarih6cyag1.jpg)，可见带打印层纹的多种嵌套多边形成品。可探索花瓣、波纹或徽章式轴向滑动；静态照片不证明完整行程、防脱或耐久。

**待补：实际原版 FreeCAD 工程、文件版本与具体 GPL 许可文本／版本。** 原模型页当前不可读，尚未取回工程，不记录虚构文件名、校验值、材料或件数。[JeremyADay 的 OpenSCAD 移植](https://github.com/JeremyADay/parametric-polygon-fidget)虽有可读代码，但许可仅转指原模型，README 所称随附 FreeCAD 文件未见于实际目录；不把原作实拍转作该移植的验证。补齐原作证据后保护环间锥面、间隙、行程和防脱几何，再按轮廓、尺度及材料改动检查卡滞、拉脱与夹点。

## W13–W14：轻质套层伸缩玩具

以下为 2026-11-13 新增的待核查卡，只用于手动拉伸／收合的轻质解压玩具、层叠摆件或展示道具。本组两项仍未进入正式机构卡；不能将公开代码、免费文件或“可定制”标签写成已获改编许可，也不能以本轮资料支撑击打用甩棍的制作或加固。

### W13 — Collapsible Cones 套层伸缩圆锥

- **动作与用途：** The Toy Engineer 的嵌套圆锥示例，可作为手动拉伸、收合和层叠展开的玩法线索。花形／小塔或角色局部伸缩属于本库适配设想，不是作者已经验证的产品。
- **一手来源与设计源：** [作者仓库](https://github.com/The-Toy-Engineer/cones)、[固定版本 README](https://github.com/The-Toy-Engineer/cones/blob/4b4af57a7e2e67f96418c6d396026115dbcf3e3a/README.md)、[实际 cones.scad](https://github.com/The-Toy-Engineer/cones/blob/4b4af57a7e2e67f96418c6d396026115dbcf3e3a/cones.scad)。本轮已读取提交 `4b4af57a7e2e67f96418c6d396026115dbcf3e3a` 的源码文本；未运行、未导入 Blender、未打印。
- **许可缺口：** 本轮读取的仓库根目录、README 和源文件未见许可证或明确改编／分发授权。状态为“源码公开、授权待核”，不是可直接复用的开源核心；取得适用授权前不复制代码到项目、不生成衍生模型或随包分发。
- **物理证据缺口：** [作者设计文章](https://medium.com/@thetoyengineer/designing-collapsible-toys-92916e83ca7c)解释用途和建模思路；本轮未取得可核验的实际打印、装配与手动收合记录，不能用几何示意替代实物验证。材料、设备条件、实际件数和耐久保持未知。
- **后续补核：** 优先取得作者明确许可及对应版本的实物记录，再按统一门槛决定升卡。若获得采用资格，仍按真实改动检查外观是否侵入运动空间、收合是否卡滞、是否有夹点或意外脱落；保持轻质非击打用途，不提供加重、冲击承载或甩出锁止的改造。

### W14 — Customizable Telescopic Fidget 参数化伸缩解压玩具

- **发现线索：** RaDu88253，[MakerWorld 原模型 491823](https://makerworld.com/en/models/491823)。[次级发现索引](https://3dgo.app/models/makerworld/491823)称其可用 OpenSCAD 自定义轮廓，并标记 BY-NC-SA；这些是待核线索，不作为原作者许可或实际设计源的证明。
- **当前缺口：** 本轮原模型页读取受限，尚未核对具体 SCAD、许可证版本／适用文件及原始实物记录。不能宣称已下载源码、已确认可商用或已验证动作；即使后续确认非商业许可，也须明确适用范围，不能混称自由商用。
- **续接条件：** 获得可读取的原作者页面、具体设计源与许可及实物记录后再补核；无新证据不重复请求受限页面。可用于共创解释“平面轮廓变为层叠立体”的玩法意向，选定意向不等于机构已可采用。

## W15–W16：伸缩抓手与套层容器

### W15 — Grab Toy ++／Infinite 剪叉伸缩抓手

- **设计源状态：** ecoiras 的 [Grab Toy ++ 原作者页](https://cults3d.com/en/3d-model/game/grab-toy)（设计 19734，2018-01-11）明确列出 GrabToyPlusPlus.scad.zip、铰链小样和两种抓手 STL，介绍 OpenSCAD 构造原位打印铰链和剪叉框；目前仍只取得作者提供源码的说明，未取回或读取实际 ZIP／SCAD。页面可读内容有缓存时效，下载前仍须核对实际版本与所附许可。
- **许可核查与当前决定：** 上述设计页同时标记 CC BY 和 No AI。[Cults 官方更新记录](https://cults3d.com/en/pages/logbook-updates-new-features-cults)的 2023-12 条目称 No AI 默认附加到平台设计、限制 AI 工具使用；2025-09 条目又记录作者可取消接受默认 NoAI 的选项。本轮取得的是官方页面的公开检索正文，完整 No AI 条款入口仍读取受限，未核明该设计是否存在适用于本流程的例外。此使用限制与[隐藏 AI 生成作品的搜索过滤器](https://cults3d.com/en/pages/filtering-ai-generated-designs)不同；不能以“只禁止训练”或“本地 Blender 操作”自行推定豁免，也不能将平台默认标签表述为作者亲自答复拒绝。**尚无可核对的适用授权，不升为正式卡，不将其文件或图片交给 AI 改造／Tripo。**
- **独立来源续查结果：** 原 Thingiverse 2750749／2768626 页面仍未成功读取；按 GrabToyPlusPlus、GrabToyInfinite、HingeSlackTest 搜索 GitHub 未取得相关设计源或许可，不能据搜索未命中声称源码不存在。[作者公开评论](https://cults3d.com/es/usuarios/ecoiras/comments)中说明 ZIP 内有剪叉模型 SCAD，并对其他用户出售打印件、打印后展示照片作出过肯定答复；这些答复不是本流程的通用授权，也不能替代具体源码许可。第三方转载、免费下载及聚合页标签不填补该缺口。
- **怎样取得采用资格：** 优先核对作者独立发布的原始设计源与其适用许可，或与该版本、拟定用途对应的明确授权；无需仅因使用 AI 就一律额外索要许可，但必须解决当前已出现的条件冲突。分别判断两条路线：① AI 助手读取／调整代码，借助 OpenSCAD／Blender 生成、修改、整合机构并依许可交付衍生成果；② 把源码、网格或图片上传 Tripo 等外部生成服务，按该服务实际数据条款处理。若只确认①，可按限定本地代码路线评估正式卡，不要求同时开放②；未获依据的上传路线保持不可用。作者授权应说明适用文件、版本、使用者范围、改编与分发／商用条件；不从允许卖打印件推导允许分享数字源码，也不从单人授权推导所有 skill 用户可用。本包仅收录摘要与链接，第三方素材另守原许可。
- **物理记录与家族边界：** ++ 作者记录 Anycubic I3+、PLA、0.2 mm 层高的试印和铰链配合经验；短／长版有一／三组伸展框，独立运动实体数仍需实际源文件核对。[Infinite 原页](https://cults3d.com/en/3d-model/game/grab-toy-infinite)为框数参数化版本；[Adafruit 自行打印记录](https://blog.adafruit.com/2018/03/01/grab-toy-infinite-timelapse-3dprinting-3dthursday/)列出 Ultimaker 2+、紫色 PLA、0.2 mm 层高及 0.4 mm 喷嘴，已读文字，未逐帧核验视频。此记录只对应 Infinite，不能借用 ++ 的许可或断言任意框数可用；二者同一机构家族，不重复计卡。本机未生成或打印，无额定抓力／循环寿命结论。
- **采用后的保护与验证：** 保护铰链、轴距、连杆根部、平面错层与夹点；加长或更换抓爪后检查质量、力臂和摩擦累积。作者通过薄缝引导额外壁线的设计需核对切片意图，不默认当破面填平；只有原配合证据不适用时才补必要铰链小样。可探索轻质手动抓取或角色手臂伸展，保持与套层伸缩的动作区别。下一次仅在原始文件及许可、可读的独立发布入口或明确授权等新证据出现后续查，不重复请求同一受限页面。

### W16 — Collapsibasket（已转正式卡 M15）

2026-11-13 已实际运行固定版本最小依赖组合，核对所用许可，并在 Blender 检查默认输出与作者 STL 的几何一致性；采用范围、依赖清单、软件验证及实物证据边界统一见 [M15 正式卡](toy-mechanisms.md#m15--套层升降与转位保持-collapsibasket)。本项只保留编号追踪，不再计入待查，也不重复计为另一张机构卡。原 get_deps.sh 的整套依赖未经同等验证，不因本卡升格而自动可用。

## 待查项怎样续接

仅在获得新的一手许可、源文件目录／原始下载、实际打印／装配记录，或用户提供的获许可设计源等可核对证据时继续补核。说明新证据补齐哪项缺口，记录版本及实际文件校验值，再按统一门槛评估是否升为正式方案卡；实物照片补齐不能代替许可或源码核对。没有新入口或证据时不反复请求同一受限页面，也不让待查项阻塞已确认候选的使用。实际文件仍只有 STL 时保留普通参考状态，不虚构参数源；用户明确选择网格改造时按现有建模规则另评估，不把它改记为设计源已核实。不得绕过登录、付费或下载限制。
