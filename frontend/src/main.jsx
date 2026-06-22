import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  Archive,
  Bot,
  Camera,
  CheckCircle2,
  Database,
  FileSearch,
  Folder,
  FolderOpen,
  Languages,
  Moon,
  Play,
  RefreshCw,
  RotateCcw,
  Save,
  ScanFace,
  Search,
  Settings,
  Sun,
  Tags,
  TerminalSquare,
  Users,
  XCircle,
} from 'lucide-react';
import './styles.css';

const i18n = {
  en: {
    app: 'TG Media',
    manager: 'Manager',
    title: 'Media Operations',
    dashboard: 'Dashboard',
    jobs: 'Jobs',
    library: 'Library',
    virtualLibrary: 'Virtual Library',
    authors: 'Authors',
    faces: 'Face Groups',
    logs: 'Logs',
    settings: 'Settings',
    all: 'All',
    manifest: 'Manifest',
    move_plan: 'Move Plan',
    applied: 'Applied',
    filename_words: 'Words',
    filename_analysis: 'Name Signals',
    searchPlaceholder: 'Search manifests',
    actors: 'Actors',
    keywords: 'Keywords',
    unknown: 'Unknown',
    duplicates: 'Duplicates',
    frameCache: 'Frame Cache',
    faceRows: 'Face Rows',
    facePlan: 'Face Plan',
    faceMergeSuggestions: 'Face Merge Suggestions',
    visionPlan: 'Vision Plan',
    exactDuplicates: 'Exact Duplicates',
    wordSignals: 'Word Signals',
    runJobs: 'Run Jobs',
    commandGuide: 'Command Guide',
    advancedCommands: 'Advanced commands',
    commonCommands: 'Common',
    faceCommands: 'Face',
    visionCommands: 'Vision',
    maintenanceCommands: 'Maintenance',
    dangerousCommands: 'Moves files',
    recommendedWorkflows: 'Recommended Workflows',
    newDownloadsWorkflow: 'New downloads',
    newDownloadsHint: 'Scan, mine names, classify keywords, apply the current move plan, then refresh.',
    reviewCleanupWorkflow: 'Clean review',
    reviewCleanupHint: 'Normalize existing folders, classify review items, remove non-media clutter, and dedupe.',
    faceWorkflow: 'Rebuild faces',
    faceWorkflowHint: 'Extract frames, scan faces, cluster with balanced threshold, build face plan.',
    visionWorkflow: 'Scene labels',
    visionWorkflowHint: 'Run local OpenCLIP scene/category labels and create a dry-run move plan.',
    ready: 'Ready',
    running: 'Running',
    starting: 'Starting...',
    keywordBuckets: 'Keyword Buckets',
    visionPipeline: 'Vision Pipeline',
    localOnly: 'local only',
    sourceLeftovers: 'Source Leftovers',
    workbench: 'Workbench',
    workbenchHint: 'Start from the queue with the highest count. Workflows run multiple safe jobs in sequence and show the next step in the job log.',
    reviewQueue: 'Review queue',
    newFilesAction: 'Organize new files',
    reviewAction: 'Clean review folders',
    faceAction: 'Review face merges',
    duplicateAction: 'Preview duplicates',
    openFaces: 'Open Face Groups',
    runNext: 'Run next step',
    searchResults: 'Search Results',
    recentLogs: 'Recent Logs',
    moveLogRows: 'move log rows',
    jobLog: 'Job Log',
    selectJob: 'select a job',
    selectJobHint: 'Select a job to inspect stdout and stderr',
    command: 'Command',
    started: 'Started',
    finished: 'Finished',
    noRows: 'No rows',
    mediaRoot: 'Media source root',
    outputRoot: 'Organized library root',
    sourceDirs: 'Source subdirectories',
    sourceDirsHint: 'Comma separated. Leave empty to scan the whole source root.',
    monitor: 'Folder monitor',
    monitorEnabled: 'Auto scan new files',
    monitorDirs: 'Monitor directories',
    monitorDirsHint: 'Comma separated, relative to media root or absolute container paths. Usually same as source folders.',
    monitorInterval: 'Check interval (minutes)',
    checkNow: 'Check now',
    monitorStatus: 'Monitor status',
    language: 'Language',
    saveSettings: 'Save settings',
    syncAuthors: 'Sync authors',
    authorSearch: 'Search authors',
    sortAuthors: 'Sort authors',
    filterAuthors: 'Filter',
    authorView: 'View',
    cardView: 'Cards',
    tableView: 'Table',
    allAuthors: 'All authors',
    withThumb: 'With thumbnail',
    withoutThumb: 'Missing thumbnail',
    withFaceGroup: 'With FaceGroup',
    withoutFaceGroup: 'No FaceGroup',
    byFiles: 'Most media',
    byPhotos: 'Most photos',
    byVideos: 'Most videos',
    byFaceGroups: 'Most FaceGroups',
    byName: 'Name A-Z',
    renameTo: 'Rename / merge to',
    excludeAuthor: 'Exclude',
    authorHint: 'Rename merges folders when the target already exists. Exclude moves a mistaken author to review.',
    syncAuthorsDone: 'Authors synced',
    authorName: 'Author',
    files: 'Files',
    photos: 'Photos',
    videos: 'Videos',
    thumbnail: 'Thumbnail',
    present: 'Present',
    missing: 'Missing',
    browse: 'Browse',
    directories: 'Directories',
    currentPath: 'Current path',
    namedAs: 'Named as',
    nameActor: 'Actor name',
    saveName: 'Name group',
    unnamed: 'Unnamed',
    media: 'media',
    facesCount: 'faces',
    applyConfirm: 'Apply Plan will move files according to the current move_plan.csv. Continue?',
    applyAllConfirm: 'Apply All will move every planned file, including review items. Continue?',
    settingsSaved: 'Settings saved',
    workflowConfirm: 'This will run several jobs in sequence. Continue?',
    libraryHelp: 'The Library page shows manifest search results. Pick a source above, search by actor, keyword, path, hash, FaceGroup, or scene label.',
    libraryQuickSearch: 'Quick search',
    rebuildIndex: 'Rebuild index',
    mediaBrowser: 'Media browser',
    mediaSearch: 'Search media, tags, authors',
    allMedia: 'All media',
    photosOnly: 'Photos',
    videosOnly: 'Videos',
    openMedia: 'Open',
    mediaDetail: 'Media detail',
    originalName: 'Original name',
    filePath: 'File path',
    tags: 'Tags',
    timeline: 'Timeline',
    confidence: 'Confidence',
    noIndexHint: 'No indexed media yet. Run Rebuild index after scan/apply.',
    mergeIntoLeft: 'Merge into left',
    mergeIntoRight: 'Merge into right',
    mergeSameName: 'Merge same-name groups',
    mergeSameNameConfirm: 'Merge all FaceGroups that have the same actor name?',
    mergeSameNameDone: 'Same-name FaceGroups merged',
    faceMergeHelp: 'Lower distance means more similar. Review thumbnails, then merge only obvious same-person groups.',
    jobNextStep: 'Next step',
    faceSampleNext: 'Sample scan only creates face_index.csv. Run Cluster Balanced, then Face Report, then review Face Groups.',
    frameSampleNext: 'Frame sample only creates thumbnails. Run Face Sample or Vision Sample next.',
    visionSampleNext: 'Vision sample creates scene labels. Run Vision Plan to preview moves, then Vision Apply if it looks right.',
    commandNames: {
      'workflow-new-downloads': 'New Downloads',
      'workflow-review-cleanup': 'Review Cleanup',
      'workflow-face-balanced': 'Rebuild Faces',
      'workflow-vision-plan': 'Scene Plan',
      'index-metadata': 'Rebuild Index',
      scan: 'Scan',
      'analyze-filenames': 'Analyze Names',
      'classify-keywords': 'Keywords',
      'normalize-organized': 'Normalize',
      'refresh-state': 'Refresh State',
      'extract-frames-sample': 'Frames Sample',
      'face-setup': 'Face Setup',
      'vision-scan-sample': 'Vision Sample',
      'index-vision': 'Sync Vision',
      'face-scan-sample': 'Face Sample',
      'face-cluster': 'Cluster Faces',
      'face-cluster-balanced': 'Cluster Balanced',
      'face-cluster-relaxed': 'Cluster Relaxed',
      'face-cluster-report': 'Face Report',
      'apply-face-groups-dry-run': 'Face Plan',
      'apply-face-groups': 'Apply Faces',
      'dedupe-organized-dry-run': 'Dedupe Plan',
      'dedupe-organized': 'Dedupe Apply',
      'organize-review': 'Clean Review',
      'apply-vision-labels-dry-run': 'Vision Plan',
      'apply-vision-labels': 'Vision Apply',
      apply: 'Apply Plan',
      'apply-include-review': 'Apply All',
      'clean-empty-dirs': 'Clean Dirs',
    },
    commandHelp: {
      'workflow-new-downloads': 'Best default for new files: scan, classify, move, refresh.',
      'workflow-review-cleanup': 'Revisit Unknown/NeedsManualCheck and exact duplicates.',
      'workflow-face-balanced': 'Rebuild face index and same-face groups conservatively.',
      'workflow-vision-plan': 'Run local image scene labels and create a dry-run plan.',
      'index-metadata': 'Import organized files and manifests into the virtual SQLite library.',
      scan: 'Read source folders and write manifest_all.csv plus move_plan.csv. Does not move by itself.',
      'analyze-filenames': 'Mine filename words, actor candidates, and noisy tokens.',
      'classify-keywords': 'Move obvious Unknown items into keyword buckets.',
      'normalize-organized': 'Flatten actor folders and move weak actor names back to review.',
      'refresh-state': 'Recount dashboard numbers.',
      'extract-frames-sample': 'Cache thumbnails/frames for a small sample.',
      'face-setup': 'Show face/vision dependency status.',
      'vision-scan-sample': 'Run OpenCLIP labels on a small sample.',
      'index-vision': 'Import vision_labels.csv and frame_index.csv into tags and timeline segments.',
      'face-scan-sample': 'Detect faces on a small sample only.',
      'face-cluster': 'Cluster existing face embeddings with normal threshold.',
      'face-cluster-balanced': 'Recommended face clustering threshold.',
      'face-cluster-relaxed': 'Wider face clustering for manual review.',
      'face-cluster-report': 'Summarize face groups and merge suggestions.',
      'apply-face-groups-dry-run': 'Create face_move_plan.csv. Does not move.',
      'apply-face-groups': 'Move merged/named face groups into FaceGroup or Actor folders.',
      'dedupe-organized-dry-run': 'Find exact duplicates. Does not move.',
      'dedupe-organized': 'Move exact duplicates to review.',
      'organize-review': 'Clean Unknown/NeedsManualCheck and non-media files.',
      'apply-vision-labels-dry-run': 'Create scene/category move plan. Does not move.',
      'apply-vision-labels': 'Move Unknown/Review by scene labels.',
      apply: 'Move files according to move_plan.csv.',
      'apply-include-review': 'Move all planned files, including review items.',
      'clean-empty-dirs': 'Remove empty directories.',
    },
  },
  'zh-CN': {
    app: 'TG 媒体',
    manager: '管理器',
    title: '媒体整理',
    dashboard: '概览',
    jobs: '任务',
    library: '媒体库',
    virtualLibrary: '虚拟媒体库',
    authors: '作者',
    faces: '人脸组',
    logs: '日志',
    settings: '设置',
    all: '全部',
    manifest: '总清单',
    move_plan: '移动计划',
    applied: '已执行',
    filename_words: '词频',
    filename_analysis: '名称信号',
    searchPlaceholder: '搜索清单',
    actors: '人物',
    keywords: '关键词',
    unknown: '未知',
    duplicates: '重复',
    frameCache: '抽帧缓存',
    faceRows: '人脸记录',
    facePlan: '人脸计划',
    faceMergeSuggestions: '人脸合并建议',
    visionPlan: '场景计划',
    exactDuplicates: '精确重复',
    wordSignals: '词信号',
    runJobs: '运行任务',
    commandGuide: '功能说明',
    advancedCommands: '高级命令',
    commonCommands: '常用',
    faceCommands: '人脸',
    visionCommands: '视觉',
    maintenanceCommands: '维护',
    dangerousCommands: '会移动文件',
    recommendedWorkflows: '推荐流程',
    newDownloadsWorkflow: '整理新下载',
    newDownloadsHint: '扫描来源目录，分析名称，按关键词归类，执行移动计划，再刷新统计。',
    reviewCleanupWorkflow: '清理 Review',
    reviewCleanupHint: '规范已有目录，继续整理 Unknown/NeedsManualCheck，清理非媒体，并做精确去重。',
    faceWorkflow: '重建人脸组',
    faceWorkflowHint: '全量抽帧、人脸扫描、均衡阈值聚类，并生成人脸移动计划。',
    visionWorkflow: '场景识别计划',
    visionWorkflowHint: '用本地 OpenCLIP 做画面分类，并生成 dry-run 场景移动计划。',
    ready: '就绪',
    running: '运行中',
    starting: '启动中...',
    keywordBuckets: '关键词分组',
    visionPipeline: '视觉流水线',
    localOnly: '仅本地',
    sourceLeftovers: '来源残留',
    workbench: '工作台',
    workbenchHint: '优先处理数量最多的队列。推荐流程会连续执行多个安全任务，任务日志里会提示下一步。',
    reviewQueue: '待处理队列',
    newFilesAction: '整理新文件',
    reviewAction: '清理 Review',
    faceAction: '检查人脸合并',
    duplicateAction: '预览重复文件',
    openFaces: '打开人脸组',
    runNext: '执行下一步',
    searchResults: '搜索结果',
    recentLogs: '最近日志',
    moveLogRows: '移动日志行',
    jobLog: '任务日志',
    selectJob: '选择任务',
    selectJobHint: '选择一个任务查看 stdout 和 stderr',
    command: '命令',
    started: '开始',
    finished: '结束',
    noRows: '没有记录',
    mediaRoot: '媒体来源目录',
    outputRoot: '整理后媒体库目录',
    sourceDirs: '来源子目录',
    sourceDirsHint: '英文逗号分隔；留空则扫描整个来源目录。',
    monitor: '目录监控',
    monitorEnabled: '自动扫描新文件',
    monitorDirs: '监控目录',
    monitorDirsHint: '英文逗号分隔；可写媒体根目录下的相对目录，也可写容器内绝对路径。通常和来源子目录一致。',
    monitorInterval: '检查间隔（分钟）',
    checkNow: '立即检查',
    monitorStatus: '监控状态',
    language: '语言',
    saveSettings: '保存设置',
    syncAuthors: '同步作者目录',
    authorSearch: '搜索作者',
    sortAuthors: '作者排序',
    filterAuthors: '筛选',
    authorView: '视图',
    cardView: '卡片',
    tableView: '表格',
    allAuthors: '全部作者',
    withThumb: '有缩略图',
    withoutThumb: '缺缩略图',
    withFaceGroup: '有关联人脸',
    withoutFaceGroup: '无人脸关联',
    byFiles: '媒体最多',
    byPhotos: '照片最多',
    byVideos: '视频最多',
    byFaceGroups: '人脸组最多',
    byName: '名称 A-Z',
    renameTo: '改名 / 合并到',
    excludeAuthor: '排除',
    authorHint: '改名时如果目标作者已存在，会自动合并目录；排除会把误识别作者移到 Review。',
    syncAuthorsDone: '作者目录已同步',
    authorName: '作者',
    files: '文件',
    photos: '照片',
    videos: '视频',
    thumbnail: '缩略图',
    present: '有',
    missing: '缺失',
    browse: '浏览',
    directories: '目录',
    currentPath: '当前位置',
    namedAs: '已命名为',
    nameActor: '人物名称',
    saveName: '命名人脸组',
    unnamed: '未命名',
    media: '媒体',
    facesCount: '人脸',
    applyConfirm: 'Apply Plan 会按当前 move_plan.csv 移动文件。继续？',
    applyAllConfirm: 'Apply All 会移动所有计划文件，包括 review 项。继续？',
    settingsSaved: '设置已保存',
    workflowConfirm: '这会连续运行多个任务，继续？',
    libraryHelp: '媒体库页是清单搜索结果页：在上方选择来源，可以按人物、关键词、路径、hash、人脸组、场景标签搜索。',
    libraryQuickSearch: '快捷搜索',
    rebuildIndex: '重建索引',
    mediaBrowser: '媒体浏览',
    mediaSearch: '搜索媒体、标签、作者',
    allMedia: '全部媒体',
    photosOnly: '照片',
    videosOnly: '视频',
    openMedia: '打开',
    mediaDetail: '媒体详情',
    originalName: '原始文件名',
    filePath: '文件路径',
    tags: '标签',
    timeline: '时间轴',
    confidence: '置信度',
    noIndexHint: '还没有索引媒体。扫描/整理后先点重建索引。',
    mergeIntoLeft: '合并到左边',
    mergeIntoRight: '合并到右边',
    mergeSameName: '合并同名人脸组',
    mergeSameNameConfirm: '把所有已命名为同一个人物的人脸组自动合并？',
    mergeSameNameDone: '同名人脸组已合并',
    faceMergeHelp: '距离越小越像。先看缩略图，只有明显同一个人再合并。',
    jobNextStep: '下一步',
    faceSampleNext: '样本扫描只会生成 face_index.csv。接着点 Cluster Balanced，再点 Face Report，然后去人脸组检查。',
    frameSampleNext: '抽帧样本只生成缩略图缓存。下一步点 Face Sample 或 Vision Sample。',
    visionSampleNext: '视觉样本会生成场景标签。下一步点 Vision Plan 预览移动，再确认是否 Vision Apply。',
    commandNames: {
      'workflow-new-downloads': '整理新下载',
      'workflow-review-cleanup': '清理 Review',
      'workflow-face-balanced': '重建人脸组',
      'workflow-vision-plan': '场景识别计划',
      'index-metadata': '重建索引',
      scan: '扫描清单',
      'analyze-filenames': '分析文件名',
      'classify-keywords': '关键词归类',
      'normalize-organized': '规范目录',
      'refresh-state': '刷新统计',
      'extract-frames-sample': '抽帧样本',
      'face-setup': '检查人脸环境',
      'vision-scan-sample': '视觉样本',
      'index-vision': '同步视觉索引',
      'face-scan-sample': '人脸样本',
      'face-cluster': '人脸聚类',
      'face-cluster-balanced': '均衡聚类',
      'face-cluster-relaxed': '宽松聚类',
      'face-cluster-report': '人脸报告',
      'apply-face-groups-dry-run': '人脸移动计划',
      'apply-face-groups': '执行人脸归类',
      'dedupe-organized-dry-run': '去重计划',
      'dedupe-organized': '执行去重',
      'organize-review': '清理 Review',
      'apply-vision-labels-dry-run': '场景移动计划',
      'apply-vision-labels': '执行场景归类',
      apply: '执行移动计划',
      'apply-include-review': '执行全部移动',
      'clean-empty-dirs': '清空目录',
    },
    commandHelp: {
      'workflow-new-downloads': '新文件首选：扫描、分析、关键词归类、执行移动、刷新统计。',
      'workflow-review-cleanup': '重新整理 Unknown/NeedsManualCheck，并做精确去重。',
      'workflow-face-balanced': '重新抽帧、人脸扫描、保守聚类，生成新的人脸计划。',
      'workflow-vision-plan': '本地识别画面场景/标签，只生成预览计划。',
      'index-metadata': '把已整理文件和清单导入 SQLite 虚拟媒体库。',
      scan: '读取来源目录，生成 manifest_all.csv 和 move_plan.csv；本身不移动。',
      'analyze-filenames': '挖掘文件名里的人名、关键词、噪声词。',
      'classify-keywords': '把明显的 Unknown 文件移动到关键词分类。',
      'normalize-organized': '整理已有演员目录，把不靠谱的人名移回 review。',
      'refresh-state': '重新统计首页数字。',
      'extract-frames-sample': '只抽一小批缩略图/视频帧，供测试。',
      'face-setup': '检查人脸/视觉依赖是否可用。',
      'vision-scan-sample': '只对小样本跑场景识别。',
      'index-vision': '把 vision_labels.csv 和 frame_index.csv 导入标签和时间轴。',
      'face-scan-sample': '只对小样本检测人脸。',
      'face-cluster': '用普通阈值聚类已有的人脸特征。',
      'face-cluster-balanced': '推荐阈值，比较稳，不容易乱合。',
      'face-cluster-relaxed': '更宽松，适合人工检查，可能把不同人放近。',
      'face-cluster-report': '生成人脸组摘要和合并建议。',
      'apply-face-groups-dry-run': '生成 face_move_plan.csv，只预览不移动。',
      'apply-face-groups': '把合并/命名后的人脸组移动到同一个 FaceGroup 或 Actor 文件夹。',
      'dedupe-organized-dry-run': '查精确重复，只预览不移动。',
      'dedupe-organized': '把精确重复移动到 review。',
      'organize-review': '清理 Unknown/NeedsManualCheck 和非媒体文件。',
      'apply-vision-labels-dry-run': '按场景标签生成移动计划，只预览。',
      'apply-vision-labels': '按场景标签移动 Unknown/Review。',
      apply: '按 move_plan.csv 移动文件。',
      'apply-include-review': '移动所有计划文件，包括 review 项。',
      'clean-empty-dirs': '删除整理后留下的空文件夹。',
    },
  },
};

const commands = [
  ['workflow-new-downloads', 'New Downloads', Play, 'Recommended: scan, analyze, classify, apply, refresh'],
  ['workflow-review-cleanup', 'Review Cleanup', Archive, 'Recommended: normalize, classify review, dedupe, refresh'],
  ['workflow-face-balanced', 'Rebuild Faces', Users, 'Recommended: full frames, face scan, balanced cluster, report, plan'],
  ['workflow-vision-plan', 'Scene Plan', Camera, 'Recommended: full frames, OpenCLIP labels, dry-run vision plan'],
  ['index-metadata', 'Rebuild Index', Database, 'Import organized files into the virtual media library'],
  ['scan', 'Scan', Search, 'Rebuild manifests and move plan'],
  ['analyze-filenames', 'Analyze Names', FileSearch, 'Mine actor and keyword signals'],
  ['classify-keywords', 'Keywords', Tags, 'Move clear Unknown items into keyword buckets'],
  ['normalize-organized', 'Normalize', Archive, 'Flatten actor folders and move weak actor names to review'],
  ['refresh-state', 'Refresh State', RefreshCw, 'Recount library state snapshot'],
  ['extract-frames-sample', 'Frames Sample', Camera, 'Cache frames for a small sample'],
  ['face-setup', 'Face Setup', ScanFace, 'Show local face dependency status'],
  ['vision-scan-sample', 'Vision Sample', Camera, 'Run OpenCLIP sample when CLIP image is used'],
  ['index-vision', 'Sync Vision', Camera, 'Import vision outputs into media tags and timelines'],
  ['face-scan-sample', 'Face Sample', ScanFace, 'Detect faces for a small sample'],
  ['face-cluster', 'Cluster Faces', Users, 'Group similar local face embeddings'],
  ['face-cluster-balanced', 'Cluster Balanced', Users, 'Balanced same-face clustering'],
  ['face-cluster-relaxed', 'Cluster Relaxed', Users, 'Wider clustering for manual review'],
  ['face-cluster-report', 'Face Report', Activity, 'Summarize face groups for review'],
  ['apply-face-groups-dry-run', 'Face Plan', Play, 'Create face move plan only'],
  ['apply-face-groups', 'Apply Faces', Play, 'Move face-grouped files'],
  ['dedupe-organized-dry-run', 'Dedupe Plan', Archive, 'Find exact duplicate organized files'],
  ['dedupe-organized', 'Dedupe Apply', Archive, 'Move exact duplicates to review'],
  ['organize-review', 'Clean Review', Archive, 'Classify review, move non-media, exact dedupe'],
  ['apply-vision-labels-dry-run', 'Vision Plan', Camera, 'Create scene/category move plan only'],
  ['apply-vision-labels', 'Vision Apply', Camera, 'Move Unknown/Review by scene labels'],
  ['apply', 'Apply Plan', Play, 'Move files using move_plan.csv'],
  ['apply-include-review', 'Apply All', Play, 'Move all planned files including review items'],
  ['clean-empty-dirs', 'Clean Dirs', RotateCcw, 'Remove empty organization folders'],
];

const nav = [
  ['dashboard', 'dashboard', Database],
  ['jobs', 'jobs', Activity],
  ['library', 'library', Folder],
  ['authors', 'authors', Users],
  ['faces', 'faces', Users],
  ['logs', 'logs', TerminalSquare],
  ['settings', 'settings', Settings],
];

function api(path, options) {
  return fetch(path, options).then(async response => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || response.statusText);
    return data;
  });
}

function Stat({ label, value, icon: Icon }) {
  return <div className="stat"><div className="statIcon"><Icon size={18} /></div><div><div className="statValue">{value ?? 0}</div><div className="statLabel">{label}</div></div></div>;
}

function JobBadge({ status }) {
  const Icon = status === 'done' ? CheckCircle2 : status === 'failed' ? XCircle : Activity;
  return <span className={`badge ${status}`}><Icon size={13} />{status}</span>;
}

function Empty({ label }) {
  return <div className="empty">{label}</div>;
}

function CommandButton({ command, label, Icon, help, busy, start, t }) {
  const displayLabel = t.commandNames?.[command] || label;
  const displayHelp = t.commandHelp?.[command] || help;
  return <button onClick={() => start(command)} disabled={busy} title={displayHelp}><Icon size={16} /><span>{displayLabel}</span></button>;
}

function ResultsTable({ rows, t }) {
  if (!rows?.length) return <Empty label={t.noRows} />;
  const keys = ['source', 'original_path', 'new_path', 'planned_path', 'original_name', 'canonical_actor', 'actor_candidates', 'flags', 'word', 'token', 'face_group', 'media_path'];
  return (
    <div className="tableWrap">
      <table>
        <thead><tr>{keys.map(key => <th key={key}>{key}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index}>{keys.map(key => <td key={key}>{row[key] || ''}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function App() {
  const [summary, setSummary] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [active, setActive] = useState('dashboard');
  const [busy, setBusy] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobLog, setJobLog] = useState(null);
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [results, setResults] = useState([]);
  const [mediaResults, setMediaResults] = useState({ total: 0, items: [] });
  const [authors, setAuthors] = useState([]);
  const [faces, setFaces] = useState([]);
  const [faceSuggestions, setFaceSuggestions] = useState([]);
  const [settings, setSettings] = useState(null);
  const [monitor, setMonitor] = useState(null);
  const [directories, setDirectories] = useState([]);
  const [browsePath, setBrowsePath] = useState('/media');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [language, setLanguage] = useState(() => localStorage.getItem('language') || 'zh-CN');
  const t = i18n[language] || i18n['zh-CN'];

  async function refresh() {
    const [s, j, a, f, suggestions, cfg, mon] = await Promise.all([
      api('/api/summary'),
      api('/api/jobs'),
      api('/api/authors').catch(() => []),
      api('/api/face-groups').catch(() => []),
      api('/api/face-merge-suggestions').catch(() => []),
      api('/api/settings').catch(() => null),
      api('/api/monitor').catch(() => null),
    ]);
    setSummary(s);
    setJobs(j);
    setAuthors(a);
    setFaces(f);
    setFaceSuggestions(suggestions);
    setMonitor(mon);
    if (cfg) {
      setSettings(cfg);
      setBrowsePath(cfg.media_root || '/media');
    }
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  useEffect(() => {
    refresh().catch(exc => setError(exc.message));
    loadMedia().catch(() => {});
    const id = setInterval(() => refresh().catch(() => {}), 4000);
    return () => clearInterval(id);
  }, []);

  async function start(command) {
    if (command.startsWith('workflow-')) {
      const ok = window.confirm(t.workflowConfirm);
      if (!ok) return;
    }
    if (command.startsWith('apply') && command !== 'apply-face-groups-dry-run') {
      const ok = window.confirm(command === 'apply-include-review' ? t.applyAllConfirm : t.applyConfirm);
      if (!ok) return;
    }
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const created = await api('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command }) });
      await refresh();
      await openJob(created.id);
      setActive('jobs');
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  async function openJob(id) {
    const [job, log] = await Promise.all([api(`/api/jobs/${id}`), api(`/api/jobs/${id}/log`)]);
    setSelectedJob(job);
    setJobLog(log);
  }

  async function runSearch(event) {
    event?.preventDefault();
    return performSearch(query, source);
  }

  async function performSearch(nextQuery, nextSource) {
    setError('');
    try {
      const data = await api(`/api/search?q=${encodeURIComponent(nextQuery)}&source=${encodeURIComponent(nextSource)}&limit=200`);
      setResults(data.results);
      setActive('library');
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function loadMedia(params = {}) {
    const search = new URLSearchParams({
      q: params.q || '',
      media_type: params.media_type || 'all',
      tag: params.tag || '',
      author: params.author || '',
      limit: String(params.limit || 80),
      offset: String(params.offset || 0),
    });
    const data = await api(`/api/media?${search.toString()}`);
    setMediaResults(data);
    return data;
  }

  async function saveSettings(next) {
    setError('');
    setMessage('');
    try {
      const saved = await api('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(next) });
      setSettings(saved);
      setLanguage(saved.language || language);
      setMessage(t.settingsSaved);
      await refresh();
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function browse(path) {
    setError('');
    try {
      const data = await api(`/api/directories?path=${encodeURIComponent(path)}`);
      setBrowsePath(data.path);
      setDirectories(data.directories || []);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function nameFace(faceGroup, actorName) {
    if (!actorName.trim()) return;
    setError('');
    try {
      await api('/api/face-groups/name', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ face_group: faceGroup, actor_name: actorName.trim() }) });
      await refresh();
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function mergeFace(sourceGroup, targetGroup) {
    if (!sourceGroup || !targetGroup || sourceGroup === targetGroup) return;
    const ok = window.confirm(`${sourceGroup} -> ${targetGroup}`);
    if (!ok) return;
    setError('');
    try {
      await api('/api/face-groups/merge', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_group: sourceGroup, target_group: targetGroup }) });
      await refresh();
      setMessage(`${sourceGroup} -> ${targetGroup}`);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function mergeNamedFaces(actorName = '') {
    const ok = window.confirm(t.mergeSameNameConfirm);
    if (!ok) return;
    setError('');
    try {
      await api('/api/face-groups/merge-named', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor_name: actorName }) });
      await refresh();
      setMessage(t.mergeSameNameDone);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function renameAuthor(oldName, newName) {
    if (!oldName || !newName.trim() || oldName === newName.trim()) return;
    const ok = window.confirm(`${oldName} -> ${newName.trim()}`);
    if (!ok) return;
    setError('');
    try {
      await api('/api/authors/rename', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ old_name: oldName, new_name: newName.trim() }) });
      await refresh();
      setMessage(`${oldName} -> ${newName.trim()}`);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function excludeAuthor(actorName) {
    const ok = window.confirm(`${t.excludeAuthor}: ${actorName}`);
    if (!ok) return;
    setError('');
    try {
      await api('/api/authors/exclude', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor_name: actorName }) });
      await refresh();
      setMessage(`${t.excludeAuthor}: ${actorName}`);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function syncAuthors() {
    setError('');
    try {
      await api('/api/authors/sync', { method: 'POST' });
      await refresh();
      setMessage(t.syncAuthorsDone);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function checkMonitorNow() {
    setError('');
    try {
      await api('/api/monitor/check', { method: 'POST' });
      setMessage(t.checkNow);
      await refresh();
    } catch (exc) {
      setError(exc.message);
    }
  }

  const top = summary?.top || {};
  const applied = summary?.applied || { rows: 0, status: {} };
  const leftovers = summary?.source_leftovers || {};
  const vision = summary?.vision || {};
  const analysis = summary?.analysis || {};
  const hasRunning = useMemo(() => jobs.some(job => job.status === 'running' || job.status === 'queued'), [jobs]);

  return (
    <main>
      <aside>
        <div className="brand"><Bot size={22} /><div><strong>{t.app}</strong><span>{t.manager}</span></div></div>
        <nav>{nav.map(([id, labelKey, Icon]) => <button className={active === id ? 'active' : ''} key={id} onClick={() => setActive(id)}><Icon size={16} /> {t[labelKey]}</button>)}</nav>
      </aside>

      <section className="content">
        <header>
          <div><h1>{t.title}</h1><p>{summary?.root || '/media'} {summary?.output_root && summary.output_root !== summary.root ? `-> ${summary.output_root}` : ''}</p></div>
          <div className="headerActions">
            <form className="searchForm" onSubmit={runSearch}>
              <select value={source} onChange={event => setSource(event.target.value)} title="Search source">
                {['all', 'manifest', 'move_plan', 'applied', 'filename_words', 'filename_analysis', 'face_groups', 'face_merge_suggestions', 'vision_labels', 'vision_move_plan', 'organized_duplicates'].map(item => <option value={item} key={item}>{t[item] || item}</option>)}
              </select>
              <input value={query} onChange={event => setQuery(event.target.value)} placeholder={t.searchPlaceholder} />
              <button type="submit" title="Search"><Search size={16} /></button>
            </form>
            <button className="iconButton" onClick={() => setLanguage(language === 'zh-CN' ? 'en' : 'zh-CN')} title={t.language}><Languages size={18} /></button>
            <button className="iconButton" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Theme">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
            <button className="iconButton" onClick={refresh} title="Refresh"><RefreshCw size={18} /></button>
          </div>
        </header>

        {error && <div className="alert">{error}</div>}
        {message && <div className="notice">{message}</div>}

        {active === 'dashboard' && (
          <>
            <section className="statsGrid">
              <Stat label={t.actors} value={top.actors} icon={Users} />
              <Stat label={t.keywords} value={top.keywords} icon={Tags} />
              <Stat label={t.unknown} value={top.unknown} icon={Folder} />
              <Stat label={t.duplicates} value={top.duplicates} icon={Archive} />
              <Stat label={t.frameCache} value={vision.cached_media} icon={Camera} />
              <Stat label={t.faceRows} value={vision.face_index_rows} icon={ScanFace} />
              <Stat label={t.faces} value={vision.face_report_rows || vision.face_group_rows} icon={Users} />
              <Stat label={t.facePlan} value={vision.face_move_plan_rows} icon={Play} />
              <Stat label={t.faceMergeSuggestions} value={vision.face_merge_suggestion_rows} icon={Users} />
              <Stat label={t.visionPlan} value={vision.vision_move_plan_rows} icon={Camera} />
              <Stat label={t.exactDuplicates} value={vision.organized_duplicate_rows} icon={Archive} />
              <Stat label={t.filename_analysis} value={analysis.filename_analysis_rows} icon={Search} />
              <Stat label={t.wordSignals} value={analysis.filename_words_rows} icon={Tags} />
            </section>
            <WorkbenchPanel summary={summary} leftovers={leftovers} vision={vision} start={start} setActive={setActive} busy={busy || hasRunning} t={t} />
            <WorkflowPanel t={t} start={start} busy={busy || hasRunning} />
            <details className="panel advancedPanel">
              <summary><span>{t.advancedCommands}</span><small>{t.commandGuide}</small></summary>
              <CommandGuide t={t} />
              <div className="panelHead"><h2>{t.runJobs}</h2><span>{busy ? t.starting : hasRunning ? t.running : t.ready}</span></div>
              <div className="commandGrid">{commands.map(([command, label, Icon, help]) => <CommandButton key={command} command={command} label={label} Icon={Icon} help={help} busy={busy || hasRunning} start={start} t={t} />)}</div>
            </details>
            <section className="twoCol"><BucketPanel title={t.keywordBuckets} rows={summary?.keywords || []} /><VisionPanel vision={vision} t={t} /><SourcePanel leftovers={leftovers} title={t.sourceLeftovers} /></section>
          </>
        )}

        {active === 'jobs' && <section className="twoCol jobsLayout"><JobsPanel jobs={jobs} openJob={openJob} t={t} /><LogPanel selectedJob={selectedJob} jobLog={jobLog} start={start} setActive={setActive} t={t} /></section>}
        {active === 'library' && <LibraryPanel results={results} mediaResults={mediaResults} loadMedia={loadMedia} start={start} performSearch={performSearch} setQuery={setQuery} setSource={setSource} t={t} />}
        {active === 'authors' && <AuthorsPanel authors={authors} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} syncAuthors={syncAuthors} t={t} />}
        {active === 'faces' && <FaceGroupsPanel faces={faces} suggestions={faceSuggestions} nameFace={nameFace} mergeFace={mergeFace} mergeNamedFaces={mergeNamedFaces} t={t} />}
        {active === 'logs' && <LogsPanel jobs={jobs} applied={applied} openJob={openJob} setActive={setActive} t={t} />}
        {active === 'settings' && <SettingsPanel settings={settings} setSettings={setSettings} saveSettings={saveSettings} browse={browse} directories={directories} browsePath={browsePath} monitor={monitor} checkMonitorNow={checkMonitorNow} t={t} />}
      </section>
    </main>
  );
}

function BucketPanel({ title, rows }) {
  return <div className="panel"><div className="panelHead"><h2>{title}</h2><span>{rows.length}</span></div><div className="list">{rows.map(item => <div className="row" key={item.name}><span>{item.name}</span><strong>{item.files}</strong></div>)}</div></div>;
}

function WorkbenchPanel({ summary, leftovers, vision, start, setActive, busy, t }) {
  const leftoverTotal = Object.values(leftovers || {}).reduce((a, b) => a + b, 0);
  const reviewTotal = Number(summary?.top?.unknown || 0) + Number(summary?.top?.duplicates || 0);
  const faceSuggestions = Number(vision?.face_merge_suggestion_rows || 0);
  const duplicateRows = Number(vision?.organized_duplicate_rows || 0);
  const cards = [
    [t.newDownloadsWorkflow, leftoverTotal, t.sourceLeftovers, t.newFilesAction, () => start('workflow-new-downloads'), Search],
    [t.reviewCleanupWorkflow, reviewTotal, t.reviewQueue, t.reviewAction, () => start('workflow-review-cleanup'), Archive],
    [t.faceMergeSuggestions, faceSuggestions, t.faces, t.faceAction, () => setActive('faces'), Users],
    [t.exactDuplicates, duplicateRows, t.duplicates, t.duplicateAction, () => start('dedupe-organized-dry-run'), Archive],
  ];
  return (
    <section className="panel">
      <div className="panelHead"><h2>{t.workbench}</h2><span>{t.ready}</span></div>
      <div className="hintBox"><span>{t.workbenchHint}</span></div>
      <div className="workbenchGrid">
        {cards.map(([title, value, label, action, onClick, Icon]) => (
          <button className="workbenchCard" disabled={busy && action !== t.faceAction} key={title} onClick={onClick}>
            <Icon size={18} />
            <span>{label}</span>
            <strong>{value}</strong>
            <b>{action}</b>
          </button>
        ))}
      </div>
    </section>
  );
}

function WorkflowPanel({ t, start, busy }) {
  const workflows = [
    ['workflow-new-downloads', t.newDownloadsWorkflow, t.newDownloadsHint, Search],
    ['workflow-review-cleanup', t.reviewCleanupWorkflow, t.reviewCleanupHint, Archive],
    ['workflow-face-balanced', t.faceWorkflow, t.faceWorkflowHint, Users],
    ['workflow-vision-plan', t.visionWorkflow, t.visionWorkflowHint, Camera],
  ];
  return (
    <section className="panel">
      <div className="panelHead"><h2>{t.recommendedWorkflows}</h2><span>{busy ? t.running : t.ready}</span></div>
      <div className="workflowGrid">
        {workflows.map(([command, title, hint, Icon]) => (
          <button className="workflowCard" disabled={busy} key={command} onClick={() => start(command)}>
            <Icon size={18} />
            <strong>{title}</strong>
            <span>{hint}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function CommandGuide({ t }) {
  const groups = [
    [t.commonCommands, ['workflow-new-downloads', 'workflow-review-cleanup', 'scan', 'apply']],
    [t.faceCommands, ['workflow-face-balanced', 'face-scan-sample', 'face-cluster-balanced', 'face-cluster-report', 'apply-face-groups-dry-run', 'apply-face-groups']],
    [t.visionCommands, ['workflow-vision-plan', 'vision-scan-sample', 'index-vision', 'apply-vision-labels-dry-run', 'apply-vision-labels']],
    [t.maintenanceCommands, ['refresh-state', 'dedupe-organized-dry-run', 'dedupe-organized', 'clean-empty-dirs']],
  ];
  return (
    <div className="guideSection">
      <div className="panelHead"><h2>{t.commandGuide}</h2><span>{t.runJobs}</span></div>
      <div className="guideGrid">
        {groups.map(([title, ids]) => (
          <div className="guideCard" key={title}>
            <strong>{title}</strong>
            {ids.map(id => <p key={id}><b>{t.commandNames?.[id] || id}</b>: {t.commandHelp?.[id]}</p>)}
          </div>
        ))}
      </div>
    </div>
  );
}

function VisionPanel({ vision, t }) {
  return <div className="panel"><div className="panelHead"><h2>{t.visionPipeline}</h2><span>{t.localOnly}</span></div><div className="list">{['frame_index_rows', 'face_index_rows', 'face_group_rows', 'vision_label_rows', 'face_move_plan_rows'].map(key => <div className="row" key={key}><span>{key.replace('_rows', '.csv')}</span><strong>{vision[key] || 0}</strong></div>)}</div></div>;
}

function SourcePanel({ leftovers, title }) {
  return <div className="panel"><div className="panelHead"><h2>{title}</h2><span>{Object.values(leftovers).reduce((a, b) => a + b, 0)}</span></div><div className="list">{Object.entries(leftovers).map(([name, files]) => <div className="row" key={name}><span>{name}</span><strong>{files}</strong></div>)}</div></div>;
}

function JobsPanel({ jobs, openJob, t }) {
  return <div className="panel"><div className="panelHead"><h2>{t.jobs}</h2><span>{jobs.length}</span></div><div className="jobs">{jobs.map(job => <button className="job" key={job.id} onClick={() => openJob(job.id)}><div><strong>#{job.id} {job.command}</strong><p>{job.message || job.created_at}</p></div><JobBadge status={job.status} /></button>)}</div></div>;
}

function jobNextStep(command, t) {
  if (command === 'face-scan-sample') return t.faceSampleNext;
  if (command === 'extract-frames-sample') return t.frameSampleNext;
  if (command === 'vision-scan-sample') return t.visionSampleNext;
  return '';
}

function jobNextActions(command, t, start, setActive) {
  if (command === 'face-scan-sample') {
    return [
      [t.commandNames['face-cluster-balanced'], () => start('face-cluster-balanced')],
      [t.commandNames['face-cluster-report'], () => start('face-cluster-report')],
      [t.openFaces, () => setActive('faces')],
    ];
  }
  if (command === 'extract-frames-sample') {
    return [
      [t.commandNames['face-scan-sample'], () => start('face-scan-sample')],
      [t.commandNames['vision-scan-sample'], () => start('vision-scan-sample')],
    ];
  }
  if (command === 'vision-scan-sample') {
    return [
      [t.commandNames['apply-vision-labels-dry-run'], () => start('apply-vision-labels-dry-run')],
      [t.commandNames['apply-vision-labels'], () => start('apply-vision-labels')],
    ];
  }
  return [];
}

function LogPanel({ selectedJob, jobLog, start, setActive, t }) {
  const next = selectedJob ? jobNextStep(selectedJob.command, t) : '';
  const actions = selectedJob ? jobNextActions(selectedJob.command, t, start, setActive) : [];
  return <div className="panel"><div className="panelHead"><h2>{selectedJob ? `Job #${selectedJob.id}` : t.jobLog}</h2><span>{selectedJob?.status || t.selectJob}</span></div>{!selectedJob ? <Empty label={t.selectJobHint} /> : <div className="logBlock"><div className="list"><div className="row"><span>{t.command}</span><strong>{selectedJob.command}</strong></div><div className="row"><span>{t.started}</span><strong>{selectedJob.started_at || '-'}</strong></div><div className="row"><span>{t.finished}</span><strong>{selectedJob.finished_at || '-'}</strong></div></div>{next && <div className="hintBox"><strong>{t.jobNextStep}</strong><span>{next}</span>{actions.length > 0 && <div className="nextActions">{actions.map(([label, action]) => <button key={label} onClick={action}><Play size={15} />{label}</button>)}</div>}</div>}<h3>stdout</h3><pre>{jobLog?.stdout || '(empty)'}</pre><h3>stderr</h3><pre>{jobLog?.stderr || '(empty)'}</pre></div>}</div>;
}

function LibraryPanel({ results, mediaResults, loadMedia, start, performSearch, setQuery, setSource, t }) {
  const [mediaQuery, setMediaQuery] = useState('');
  const [mediaType, setMediaType] = useState('all');
  const quick = [
    ['filename_words', 'JK'],
    ['face_merge_suggestions', 'FaceGroup'],
    ['vision_labels', '水手服'],
    ['organized_duplicates', 'duplicate'],
  ];
  function quickSearch(src, value) {
    setSource(src);
    setQuery(value);
    performSearch(value, src);
  }
  function runMediaSearch(event) {
    event?.preventDefault();
    loadMedia({ q: mediaQuery, media_type: mediaType });
  }
  return (
    <>
      <section className="panel">
        <div className="panelHead"><h2>{t.virtualLibrary}</h2><button className="panelButton" onClick={() => start('index-metadata')}><Database size={16} />{t.rebuildIndex}</button><span>{mediaResults.total || 0}</span></div>
        <div className="hintBox"><span>{t.noIndexHint}</span></div>
        <form className="mediaSearchBar" onSubmit={runMediaSearch}>
          <select value={mediaType} onChange={event => { setMediaType(event.target.value); loadMedia({ q: mediaQuery, media_type: event.target.value }); }}>
            <option value="all">{t.allMedia}</option>
            <option value="photo">{t.photosOnly}</option>
            <option value="video">{t.videosOnly}</option>
          </select>
          <input value={mediaQuery} onChange={event => setMediaQuery(event.target.value)} placeholder={t.mediaSearch} />
          <button type="submit"><Search size={16} />{t.searchResults}</button>
        </form>
        <MediaGrid items={mediaResults.items || []} loadMedia={loadMedia} t={t} />
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.library}</h2><span>{t.libraryQuickSearch}</span></div>
        <div className="hintBox"><span>{t.libraryHelp}</span></div>
        <div className="quickGrid">{quick.map(([src, value]) => <button key={`${src}-${value}`} onClick={() => quickSearch(src, value)}>{src}: {value}</button>)}</div>
      </section>
      <section className="panel"><div className="panelHead"><h2>{t.searchResults}</h2><span>{results.length} rows</span></div><ResultsTable rows={results} t={t} /></section>
    </>
  );
}

function MediaGrid({ items, t }) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  async function open(item) {
    setSelected(item);
    const data = await api(`/api/media/${item.id}`);
    setDetail(data);
  }
  if (!items?.length) return <Empty label={t.noRows} />;
  return (
    <>
      <div className="mediaGrid">
        {items.map(item => (
          <button className="mediaCard" key={item.id} onClick={() => open(item)}>
            <div className="mediaThumb">
              <img src={`/api/media/${item.id}/thumbnail`} alt={item.filename} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} />
              <span>{item.media_type === 'video' ? 'VID' : 'IMG'}</span>
            </div>
            <div className="mediaMeta">
              <strong>{item.author || item.person || item.filename}</strong>
              <p>{item.filename}</p>
              <div className="faceStats">
                <span>{item.media_type}</span>
                {item.quality && <span>{item.quality}</span>}
                {item.scene && <span>{item.scene}</span>}
              </div>
            </div>
          </button>
        ))}
      </div>
      {selected && <MediaViewer item={selected} detail={detail} close={() => { setSelected(null); setDetail(null); }} t={t} />}
    </>
  );
}

function MediaViewer({ item, detail, close, t }) {
  const data = detail || item;
  const tags = Array.isArray(data.tags) ? data.tags : String(data.tags || '').split(',').filter(Boolean).map(tag => ({ tag }));
  const timeline = Array.isArray(data.timeline) ? data.timeline : [];
  return (
    <div className="viewerBackdrop" role="dialog" aria-modal="true">
      <div className="viewerPanel">
        <div className="viewerHead"><h2>{t.mediaDetail}</h2><button className="iconButton" onClick={close}><XCircle size={18} /></button></div>
        <div className="viewerBody">
          <div className="viewerMedia">
            {data.media_type === 'video' ? <video src={`/api/media/${data.id}/file`} controls poster={`/api/media/${data.id}/thumbnail`} /> : <img src={`/api/media/${data.id}/file`} alt={data.filename} />}
          </div>
          <div className="viewerInfo">
            <div className="list">
              <div className="row"><span>{t.authorName}</span><strong>{data.author || '-'}</strong></div>
              <div className="row"><span>{t.originalName}</span><strong>{data.original_name || data.filename}</strong></div>
              <div className="row"><span>{t.filePath}</span><strong>{data.relative_path || data.filename}</strong></div>
              <div className="row"><span>{t.thumbnail}</span><strong>{data.resolution || data.quality || '-'}</strong></div>
              <div className="row"><span>{t.media}</span><strong>{data.media_type}</strong></div>
            </div>
            <h3>{t.tags}</h3>
            <div className="tagCloud">{tags.map(tag => <span key={`${tag.tag}-${tag.source || ''}`}>{tag.tag}{tag.confidence ? ` ${Math.round(Number(tag.confidence) * 100)}%` : ''}</span>)}</div>
            {timeline.length > 0 && (
              <>
                <h3>{t.timeline}</h3>
                <div className="timelineList">
                  {timeline.map((segment, index) => (
                    <div className="timelineRow" key={`${segment.start_seconds}-${index}`}>
                      <span>{formatSeconds(segment.start_seconds)} - {formatSeconds(segment.end_seconds)}</span>
                      <strong>{segment.label}</strong>
                      <em>{Math.round(Number(segment.confidence || 0) * 100)}%</em>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function formatSeconds(value) {
  const seconds = Math.max(0, Math.floor(Number(value || 0)));
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${minutes}:${String(remain).padStart(2, '0')}`;
}

function AuthorsPanel({ authors, renameAuthor, excludeAuthor, syncAuthors, t }) {
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState('files');
  const [scope, setScope] = useState('all');
  const [view, setView] = useState('cards');
  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return [...authors]
      .filter(author => {
        if (needle && !author.name.toLowerCase().includes(needle)) return false;
        if (scope === 'with-thumb') return !!author.has_thumbnail;
        if (scope === 'without-thumb') return !author.has_thumbnail;
        if (scope === 'with-face') return Number(author.face_groups || 0) > 0;
        if (scope === 'without-face') return Number(author.face_groups || 0) === 0;
        return true;
      })
      .sort((a, b) => {
        if (sort === 'name') return a.name.localeCompare(b.name, 'zh-Hans-CN');
        const key = sort === 'photos' ? 'photos' : sort === 'videos' ? 'videos' : sort === 'faces' ? 'face_groups' : 'files';
        return Number(b[key] || 0) - Number(a[key] || 0) || a.name.localeCompare(b.name, 'zh-Hans-CN');
      });
  }, [authors, filter, sort, scope]);
  return (
    <>
      <section className="panel">
        <div className="panelHead"><h2>{t.authors}</h2><button className="panelButton" onClick={syncAuthors}><RefreshCw size={16} />{t.syncAuthors}</button><span>{filtered.length}/{authors.length}</span></div>
        <div className="hintBox"><span>{t.authorHint}</span></div>
        <div className="authorToolbar">
          <input value={filter} onChange={event => setFilter(event.target.value)} placeholder={t.authorSearch} />
          <select value={sort} onChange={event => setSort(event.target.value)} title={t.sortAuthors}>
            <option value="files">{t.byFiles}</option>
            <option value="photos">{t.byPhotos}</option>
            <option value="videos">{t.byVideos}</option>
            <option value="faces">{t.byFaceGroups}</option>
            <option value="name">{t.byName}</option>
          </select>
          <select value={scope} onChange={event => setScope(event.target.value)} title={t.filterAuthors}>
            <option value="all">{t.allAuthors}</option>
            <option value="with-thumb">{t.withThumb}</option>
            <option value="without-thumb">{t.withoutThumb}</option>
            <option value="with-face">{t.withFaceGroup}</option>
            <option value="without-face">{t.withoutFaceGroup}</option>
          </select>
          <div className="segmented" aria-label={t.authorView}>
            <button className={view === 'cards' ? 'active' : ''} onClick={() => setView('cards')}>{t.cardView}</button>
            <button className={view === 'table' ? 'active' : ''} onClick={() => setView('table')}>{t.tableView}</button>
          </div>
          <button onClick={() => { setFilter(''); setScope('all'); setSort('files'); }}><RotateCcw size={16} /></button>
        </div>
      </section>
      {view === 'cards' ? (
        <section className="authorGrid">
          {filtered.map(author => <AuthorCard author={author} key={author.name} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />)}
        </section>
      ) : (
        <AuthorTable authors={filtered} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />
      )}
    </>
  );
}

function AuthorCard({ author, renameAuthor, excludeAuthor, t }) {
  const [target, setTarget] = useState(author.name);
  useEffect(() => setTarget(author.name), [author.name]);
  return (
    <article className="authorCard">
      <div className="authorThumb"><span>{author.name.slice(0, 2)}</span><img src={`${author.thumbnail_url}?v=${encodeURIComponent(author.files)}`} alt={author.name} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} /></div>
      <div className="authorMeta">
        <strong>{author.name}</strong>
        <div className="faceStats"><span>{author.files} {t.media}</span><span>{author.photos} {t.photos}</span><span>{author.videos} {t.videos}</span><span>{author.face_groups || 0} FaceGroups</span></div>
        <form onSubmit={event => { event.preventDefault(); renameAuthor(author.name, target); }}>
          <input value={target} onChange={event => setTarget(event.target.value)} placeholder={t.renameTo} />
          <button type="submit" title={t.renameTo}><Save size={15} /></button>
        </form>
        <button className="dangerButton" onClick={() => excludeAuthor(author.name)}><Archive size={15} />{t.excludeAuthor}</button>
      </div>
    </article>
  );
}

function AuthorTable({ authors, renameAuthor, excludeAuthor, t }) {
  if (!authors.length) return <section className="panel"><Empty label={t.noRows} /></section>;
  return (
    <section className="panel">
      <div className="tableWrap authorTable">
        <table>
          <thead><tr><th>{t.thumbnail}</th><th>{t.authorName}</th><th>{t.files}</th><th>{t.photos}</th><th>{t.videos}</th><th>FaceGroups</th><th>{t.renameTo}</th><th>{t.excludeAuthor}</th></tr></thead>
          <tbody>{authors.map(author => <AuthorTableRow author={author} key={author.name} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />)}</tbody>
        </table>
      </div>
    </section>
  );
}

function AuthorTableRow({ author, renameAuthor, excludeAuthor, t }) {
  const [target, setTarget] = useState(author.name);
  useEffect(() => setTarget(author.name), [author.name]);
  return (
    <tr>
      <td><div className="authorMiniThumb"><span>{author.name.slice(0, 1)}</span><img src={`${author.thumbnail_url}?v=${encodeURIComponent(author.files)}`} alt={author.name} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} /></div></td>
      <td title={author.name}>{author.name}</td>
      <td>{author.files}</td>
      <td>{author.photos}</td>
      <td>{author.videos}</td>
      <td>{author.face_groups || 0}</td>
      <td><form className="inlineForm" onSubmit={event => { event.preventDefault(); renameAuthor(author.name, target); }}><input value={target} onChange={event => setTarget(event.target.value)} /><button type="submit" title={t.renameTo}><Save size={14} /></button></form></td>
      <td><button className="dangerButton" onClick={() => excludeAuthor(author.name)}><Archive size={14} />{t.excludeAuthor}</button></td>
    </tr>
  );
}

function FaceGroupsPanel({ faces, suggestions, nameFace, mergeFace, mergeNamedFaces, t }) {
  return (
    <>
      <section className="panel">
        <div className="panelHead"><h2>{t.faceMergeSuggestions}</h2><span>{suggestions.length}</span></div>
        <div className="hintBox"><span>{t.faceMergeHelp}</span></div>
        {!suggestions.length ? <Empty label={t.noRows} /> : <div className="mergeGrid">{suggestions.slice(0, 40).map(item => <MergeCard item={item} key={`${item.left_group}-${item.right_group}`} mergeFace={mergeFace} t={t} />)}</div>}
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.faces}</h2><button className="panelButton" onClick={() => mergeNamedFaces('')}><Users size={16} />{t.mergeSameName}</button><span>{faces.length}</span></div>
        {!faces.length ? <Empty label={t.noRows} /> : <div className="faceGrid">{faces.map(face => <FaceCard face={face} key={face.face_group} nameFace={nameFace} t={t} />)}</div>}
      </section>
    </>
  );
}

function MergeCard({ item, mergeFace, t }) {
  const left = item.left_group;
  const right = item.right_group;
  return (
    <article className="mergeCard">
      <div className="mergeThumbs">
        <div><img src={`/api/face-groups/${left}/thumbnail`} alt={left} loading="lazy" /><span>{left}</span></div>
        <div><img src={`/api/face-groups/${right}/thumbnail`} alt={right} loading="lazy" /><span>{right}</span></div>
      </div>
      <div className="mergeMeta">
        <strong>{Number(item.distance || 0).toFixed(6)}</strong>
        <button onClick={() => mergeFace(right, left)}>{t.mergeIntoLeft}</button>
        <button onClick={() => mergeFace(left, right)}>{t.mergeIntoRight}</button>
      </div>
    </article>
  );
}

function FaceCard({ face, nameFace, t }) {
  const [actor, setActor] = useState(face.actor_name || '');
  useEffect(() => setActor(face.actor_name || ''), [face.actor_name]);
  return (
    <article className="faceCard">
      <div className="thumb"><img src={`${face.thumbnail_url}?v=${encodeURIComponent(face.representative_frame || '')}`} alt={face.face_group} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} /></div>
      <div className="faceMeta">
        <strong>{face.face_group}</strong>
        <span>{face.actor_name ? `${t.namedAs}: ${face.actor_name}` : t.unnamed}</span>
        <div className="faceStats"><span>{face.media || face.group_media_count || 0} {t.media}</span><span>{face.faces || face.group_face_count || 0} {t.facesCount}</span></div>
        <form onSubmit={event => { event.preventDefault(); nameFace(face.face_group, actor); }}>
          <input value={actor} onChange={event => setActor(event.target.value)} placeholder={t.nameActor} />
          <button type="submit" title={t.saveName}><Save size={15} /></button>
        </form>
      </div>
    </article>
  );
}

function LogsPanel({ jobs, applied, openJob, setActive, t }) {
  return <section className="panel"><div className="panelHead"><h2>{t.recentLogs}</h2><span>{applied.rows} {t.moveLogRows}</span></div><div className="jobs">{jobs.map(job => <button className="job" key={job.id} onClick={() => { openJob(job.id); setActive('jobs'); }}><div><strong>#{job.id} {job.command}</strong><p>{job.stdout || job.stderr || job.message || job.created_at}</p></div><JobBadge status={job.status} /></button>)}</div></section>;
}

function SettingsPanel({ settings, setSettings, saveSettings, browse, directories, browsePath, monitor, checkMonitorNow, t }) {
  const cfg = settings || { media_root: '/media', output_root: '/media', source_dirs: '', language: 'zh-CN', monitor_enabled: false, monitor_dirs: '', monitor_interval_minutes: 10, browse_roots: ['/media'] };
  function update(key, value) {
    setSettings({ ...cfg, [key]: value });
  }
  return (
    <section className="twoCol settingsLayout">
      <div className="panel">
        <div className="panelHead"><h2>{t.settings}</h2><span>{cfg.language}</span></div>
        <div className="formGrid">
          <label>{t.mediaRoot}<input value={cfg.media_root || ''} onChange={event => update('media_root', event.target.value)} /></label>
          <label>{t.outputRoot}<input value={cfg.output_root || ''} onChange={event => update('output_root', event.target.value)} /></label>
          <label>{t.sourceDirs}<input value={cfg.source_dirs || ''} onChange={event => update('source_dirs', event.target.value)} placeholder="photos,photos2,videos,videos2" /><small>{t.sourceDirsHint}</small></label>
          <div className="formSectionTitle">{t.monitor}</div>
          <label className="checkLine"><input type="checkbox" checked={!!cfg.monitor_enabled} onChange={event => update('monitor_enabled', event.target.checked)} />{t.monitorEnabled}</label>
          <label>{t.monitorDirs}<input value={cfg.monitor_dirs || ''} onChange={event => update('monitor_dirs', event.target.value)} placeholder={cfg.source_dirs || 'photos,photos2,videos,videos2'} /><small>{t.monitorDirsHint}</small></label>
          <label>{t.monitorInterval}<input type="number" min="1" max="1440" value={cfg.monitor_interval_minutes || 10} onChange={event => update('monitor_interval_minutes', event.target.value)} /></label>
          <label>{t.language}<select value={cfg.language || 'zh-CN'} onChange={event => update('language', event.target.value)}><option value="zh-CN">简体中文</option><option value="en">English</option></select></label>
          <button onClick={() => saveSettings(cfg)}><Save size={16} />{t.saveSettings}</button>
        </div>
      </div>
      <div className="panel">
        <div className="panelHead"><h2>{t.directories}</h2><span>{browsePath}</span></div>
        <div className="browseBar"><input value={browsePath} onChange={event => browse(event.target.value)} /><button onClick={() => browse(browsePath)}><FolderOpen size={16} />{t.browse}</button></div>
        <div className="dirList">{(cfg.browse_roots || []).map(path => <button key={path} onClick={() => browse(path)}>{path}</button>)}{directories.map(dir => <button key={dir.path} onClick={() => browse(dir.path)}><Folder size={15} />{dir.name}</button>)}</div>
      </div>
      <div className="panel">
        <div className="panelHead"><h2>{t.monitorStatus}</h2><span>{monitor?.enabled ? 'on' : 'off'}</span></div>
        <div className="list">
          <div className="row"><span>{t.monitorDirs}</span><strong>{(monitor?.dirs || []).join(', ') || '-'}</strong></div>
          <div className="row"><span>{t.monitorInterval}</span><strong>{monitor?.interval_minutes || cfg.monitor_interval_minutes || 10}</strong></div>
          <div className="row"><span>last check</span><strong>{monitor?.last_checked_at || '-'}</strong></div>
          <div className="row"><span>last job</span><strong>{monitor?.last_job_id || '-'}</strong></div>
        </div>
        <button className="panelButton" onClick={checkMonitorNow}><RefreshCw size={16} />{t.checkNow}</button>
      </div>
    </section>
  );
}

createRoot(document.getElementById('root')).render(<App />);
