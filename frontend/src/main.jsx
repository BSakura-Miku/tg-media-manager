import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  Archive,
  Bell,
  Bot,
  Camera,
  CheckCircle2,
  Database,
  Download,
  FileSearch,
  Film,
  Folder,
  FolderOpen,
  Grid3X3,
  HardDrive,
  Image as ImageIcon,
  Languages,
  LockKeyhole,
  Moon,
  Play,
  RefreshCw,
  RotateCcw,
  Save,
  ScanFace,
  Search,
  Settings,
  Share2,
  Shuffle,
  Mic,
  Sun,
  Tags,
  TerminalSquare,
  Trash2,
  Users,
  XCircle,
} from 'lucide-react';
import './styles.css';

const i18n = {
  en: {
    app: 'Private Library',
    manager: 'TG Media Manager',
    version: 'Version',
    build: 'build',
    title: 'Library Console',
    dashboard: 'Dashboard',
    jobs: 'Jobs',
    library: 'Library',
    virtualLibrary: 'Virtual Library',
    tagGraph: 'Tag Graph',
    randomFlow: 'Random Flow',
    models: 'Models',
    authors: 'Authors',
    faces: 'Face Groups',
    logs: 'Logs',
    settings: 'Settings',
    login: 'Login',
    password: 'Password',
    unlock: 'Unlock',
    privacyTitle: 'Privacy first',
    privacyCopy: 'Local-only processing. Media, frames, face embeddings, tags, and indexes stay on this machine/NAS.',
    all: 'All',
    manifest: 'Manifest',
    move_plan: 'Move Plan',
    applied: 'Applied',
    filename_words: 'Words',
    filename_analysis: 'Name Signals',
    searchPlaceholder: 'Search manifests',
    actors: 'Actors',
    totalMedia: 'Media total',
    totalTags: 'Tags total',
    totalAuthors: 'Authors total',
    taskRunning: 'Running jobs',
    recentAdded: 'Recently Added',
    storageSpace: 'Storage Space',
    taskList: 'Task List',
    viewAll: 'View all',
    viewAllTasks: 'View all jobs',
    usedSpace: 'Used',
    videoFiles: 'Video files',
    imageFiles: 'Image files',
    otherFiles: 'Other files',
    availableSpace: 'Available',
    dashboardGraphHint: 'Click a tag to browse matching media.',
    recentEmpty: 'No indexed media yet',
    privacyLocked: 'Privacy lock',
    viewSwitcher: 'Views',
    keywords: 'Keywords',
    unknown: 'Unknown',
    duplicates: 'Duplicates',
    frameCache: 'Frame Cache',
    faceRows: 'Face Rows',
    facePlan: 'Face Plan',
    faceMergeSuggestions: 'Face Merge Suggestions',
    visionPlan: 'Vision Plan',
    exactDuplicates: 'Exact Duplicates',
    similarityGroups: 'Similarity Groups',
    wordSignals: 'Word Signals',
    runJobs: 'Run Jobs',
    commandGuide: 'Command Guide',
    advancedCommands: 'Advanced commands',
    commonCommands: 'Common',
    faceCommands: 'Face',
    visionCommands: 'Vision',
    transcriptCommands: 'Speech',
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
    transcribeWorkflow: 'Speech to text',
    transcribeWorkflowHint: 'Extract video audio locally, transcribe speech, and make transcripts searchable.',
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
    hardware: 'Compute hardware',
    computeDevice: 'Compute mode',
    ffmpegHwaccel: 'Video decode',
    openvinoDevice: 'OpenVINO device',
    openclipModel: 'Vision model',
    openclipPretrained: 'Vision weights',
    openclipStrongModel: 'Strong rescan model',
    openclipStrongPretrained: 'Strong rescan weights',
    openclipStrongThreshold: 'Strong rescan threshold',
    openclipStrongLowOnly: 'Only rescan low-confidence media',
    openclipHint: 'Default is ViT-L-14. Use ViT-B-32 for speed; use strong rescan for low-confidence items.',
    faceProviders: 'Face inference provider',
    whisperDevice: 'Speech device',
    asrEngine: 'Speech engine',
    asrAuto: 'Auto: SenseVoice first, then Whisper',
    asrSenseVoice: 'SenseVoice GGUF',
    asrWhisper: 'faster-whisper',
    senseVoiceModel: 'SenseVoice GGUF model',
    senseVoiceBin: 'SenseVoice runner',
    senseVoiceCommand: 'Custom SenseVoice command',
    senseVoiceCommandHint: 'Optional template. Use {audio}, {model}, {bin}; leave empty for the built-in command.',
    transcribeMaxSeconds: 'Transcribe max seconds',
    transcribeFullHint: '0 means full video. Use a positive value only for quick sampling.',
    ffmpegNone: 'Software decode',
    openvinoAuto: 'OpenVINO Auto',
    cpuOnly: 'CPU only',
    gpuPreferred: 'GPU preferred',
    gpuHint: 'These settings are passed to scan, face, vision, video decode, and speech jobs. Use CPU only if the GPU driver is unstable.',
    auto: 'Auto',
    gpu: 'GPU',
    cpu: 'CPU',
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
    modelManager: 'Model Manager',
    modelRoot: 'Model root',
    modelStatus: 'Status',
    modelSize: 'Size',
    modelPath: 'Path',
    downloadModel: 'Download',
    deleteModel: 'Delete cache',
    downloadRecommended: 'Download recommended',
    modelReady: 'Ready',
    modelMissing: 'Missing',
    modelNeedsUrl: 'Needs URL env',
    modelRuntimeCache: 'Runtime cache',
    modelFile: 'File model',
    modelHint: 'Models are not baked into the Docker image. They are downloaded into /models and survive container updates.',
    deleteModelConfirm: 'Delete this cached model from /models?',
    workflowConfirm: 'This will run several jobs in sequence. Continue?',
    libraryHelp: 'The Library page shows manifest search results. Pick a source above, search by actor, keyword, path, hash, FaceGroup, or scene label.',
    libraryQuickSearch: 'Quick search',
    rebuildIndex: 'Rebuild index',
    rebuildSimilarity: 'Rebuild similarity',
    mediaBrowser: 'Media browser',
    randomMedia: 'Random media',
    randomize: 'Randomize',
    tagGraphHelp: 'Tags that often appear together are connected. Click a node or edge to search matching media.',
    tagGraphFocusHelp: 'Click a node to focus, drag it to untangle the graph, or click an edge to search media that has both tags.',
    selectedTag: 'Selected tag',
    connectedTags: 'Connected tags',
    clearFocus: 'Clear focus',
    showMedia: 'Show media',
    tagGraphEmpty: 'No tag graph yet. Rebuild index and sync vision labels first.',
    refreshGraph: 'Refresh graph',
    relatedTags: 'Related tags',
    transcript: 'Transcript',
    noTranscript: 'No transcript yet',
    mediaSearch: 'Search media, tags, authors',
    allMedia: 'All media',
    photosOnly: 'Photos',
    videosOnly: 'Videos',
    openMedia: 'Open',
    mediaDetail: 'Media detail',
    originalName: 'Original name',
    sourceOriginalPath: 'Original source path',
    indexedName: 'Library filename',
    filePath: 'File path',
    tags: 'Tags',
    tagCorrect: 'Correct',
    tagWrong: 'Wrong',
    tagFeedbackSaved: 'Feedback saved',
    trainVisionCalibrator: 'Train calibrator',
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
      'workflow-full-library': 'Full Library',
      'workflow-transcribe-sample': 'Speech Sample',
      'model-pull-recommended': 'Download Recommended Models',
      'index-metadata': 'Rebuild Index',
      'index-similarity': 'Similarity Index',
      'transcribe-sample': 'Speech Sample',
      transcribe: 'Transcribe',
      scan: 'Scan',
      'analyze-filenames': 'Analyze Names',
      'classify-keywords': 'Keywords',
      'normalize-organized': 'Normalize',
      'refresh-state': 'Refresh State',
      'extract-frames-sample': 'Frames Sample',
      'extract-frames-retry-failed': 'Retry Frames',
      'face-setup': 'Face Setup',
      'vision-scan-sample': 'Vision Sample',
      'vision-scan-strong': 'Vision Strong Rescan',
      'index-vision': 'Sync Vision',
      'train-vision-calibrator': 'Train Calibrator',
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
      'model-pull-openclip-vit-l': 'Download OpenCLIP ViT-L',
      'model-pull-openclip-vit-h': 'Download OpenCLIP ViT-H',
      'model-pull-insightface-buffalo-l': 'Download InsightFace',
      'model-pull-faster-whisper-small': 'Download Whisper Small',
      'model-pull-sensevoice-small-gguf': 'Download SenseVoice GGUF',
      'model-pull-custom-detector-onnx': 'Download Custom Detector',
    },
    commandHelp: {
      'workflow-new-downloads': 'Best default for new files: scan, classify, move, refresh.',
      'workflow-review-cleanup': 'Revisit Unknown/NeedsManualCheck and exact duplicates.',
      'workflow-face-balanced': 'Rebuild face index and same-face groups conservatively.',
      'workflow-vision-plan': 'Run local image scene labels and create a dry-run plan.',
      'workflow-full-library': 'Run scan, organize, frames, faces, scene labels, dedupe, transcription, and indexes.',
      'workflow-transcribe-sample': 'Transcribe a small sample of videos and index the text.',
      'model-pull-recommended': 'Download the default vision, face, and speech models into /models.',
      'index-metadata': 'Import organized files and manifests into the virtual SQLite library.',
      'index-similarity': 'Build exact duplicate, image perceptual hash, and video keyframe similarity groups.',
      'transcribe-sample': 'Transcribe up to 5 videos that do not have transcript text.',
      transcribe: 'Transcribe more videos that do not have transcript text.',
      scan: 'Read source folders and write manifest_all.csv plus move_plan.csv. Does not move by itself.',
      'analyze-filenames': 'Mine filename words, actor candidates, and noisy tokens.',
      'classify-keywords': 'Move obvious Unknown items into keyword buckets.',
      'normalize-organized': 'Flatten actor folders and move weak actor names back to review.',
      'refresh-state': 'Recount dashboard numbers.',
      'extract-frames-sample': 'Cache thumbnails/frames for a small sample.',
      'extract-frames-retry-failed': 'Retry rows listed in frame_errors.csv.',
      'face-setup': 'Show face/vision dependency status.',
      'vision-scan-sample': 'Run OpenCLIP labels on a small sample.',
      'vision-scan-strong': 'Use the stronger OpenCLIP model only for low-confidence media by default.',
      'index-vision': 'Import vision_labels.csv and frame_index.csv into tags and timeline segments.',
      'train-vision-calibrator': 'Train lightweight tag calibrators from manual correct/wrong feedback.',
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
      'model-pull-openclip-vit-l': 'Download/cache the default OpenCLIP vision model.',
      'model-pull-openclip-vit-h': 'Download/cache the stronger OpenCLIP model.',
      'model-pull-insightface-buffalo-l': 'Download/cache the InsightFace buffalo_l model.',
      'model-pull-faster-whisper-small': 'Download/cache the faster-whisper small fallback model.',
      'model-pull-sensevoice-small-gguf': 'Download the SenseVoice GGUF file from SENSEVOICE_GGUF_URL.',
      'model-pull-custom-detector-onnx': 'Download the optional custom detector from CUSTOM_DETECTOR_ONNX_URL.',
    },
  },
  'zh-CN': {
    app: '私享影库',
    manager: 'TG Media Manager',
    version: '版本',
    build: '构建',
    title: '影库控制台',
    dashboard: '概览',
    jobs: '任务',
    library: '媒体库',
    virtualLibrary: '虚拟媒体库',
    tagGraph: '标签图谱',
    randomFlow: '随机瀑布流',
    models: '模型',
    authors: '作者',
    faces: '人脸组',
    logs: '日志',
    settings: '设置',
    login: '登录',
    password: '密码',
    unlock: '解锁',
    privacyTitle: '隐私优先',
    privacyCopy: '全流程本地处理。媒体、抽帧、人脸特征、标签和索引都保存在这台机器/NAS。',
    all: '全部',
    manifest: '总清单',
    move_plan: '移动计划',
    applied: '已执行',
    filename_words: '词频',
    filename_analysis: '名称信号',
    searchPlaceholder: '搜索清单',
    actors: '人物',
    totalMedia: '媒体总数',
    totalTags: '标签总数',
    totalAuthors: '作者总数',
    taskRunning: '任务执行',
    recentAdded: '最近添加',
    storageSpace: '存储空间',
    taskList: '任务列表',
    viewAll: '查看全部',
    viewAllTasks: '查看全部任务',
    usedSpace: '已使用',
    videoFiles: '视频文件',
    imageFiles: '图片文件',
    otherFiles: '其他文件',
    availableSpace: '可用空间',
    dashboardGraphHint: '点击标签可浏览对应媒体。',
    recentEmpty: '还没有索引媒体',
    privacyLocked: '隐私锁定',
    viewSwitcher: '视图入口',
    keywords: '关键词',
    unknown: '未知',
    duplicates: '重复',
    frameCache: '抽帧缓存',
    faceRows: '人脸记录',
    facePlan: '人脸计划',
    faceMergeSuggestions: '人脸合并建议',
    visionPlan: '场景计划',
    exactDuplicates: '精确重复',
    similarityGroups: '相似组',
    wordSignals: '词信号',
    runJobs: '运行任务',
    commandGuide: '功能说明',
    advancedCommands: '高级命令',
    commonCommands: '常用',
    faceCommands: '人脸',
    visionCommands: '视觉',
    transcriptCommands: '语音',
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
    transcribeWorkflow: '语音转文字',
    transcribeWorkflowHint: '本地抽取视频音频，识别语音文字，并让文字进入搜索。',
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
    hardware: '计算硬件',
    computeDevice: '计算模式',
    ffmpegHwaccel: '视频解码',
    openvinoDevice: 'OpenVINO 设备',
    openclipModel: '视觉模型',
    openclipPretrained: '视觉权重',
    openclipStrongModel: '强扫视觉模型',
    openclipStrongPretrained: '强扫视觉权重',
    openclipStrongThreshold: '强扫置信阈值',
    openclipStrongLowOnly: '只复扫低置信媒体',
    openclipHint: '默认使用 ViT-L-14。需要速度可改 ViT-B-32；强扫只处理低置信项。',
    faceProviders: '人脸推理后端',
    whisperDevice: '语音识别设备',
    asrEngine: '语音识别引擎',
    asrAuto: '自动：优先 SenseVoice，再回退 Whisper',
    asrSenseVoice: 'SenseVoice GGUF',
    asrWhisper: 'faster-whisper',
    senseVoiceModel: 'SenseVoice GGUF 模型',
    senseVoiceBin: 'SenseVoice 运行器',
    senseVoiceCommand: '自定义 SenseVoice 命令',
    senseVoiceCommandHint: '可选模板。支持 {audio}、{model}、{bin}；留空则使用内置命令。',
    transcribeMaxSeconds: '每个视频识别秒数',
    transcribeFullHint: '0 表示完整识别全片；只有快速抽样时才建议填正数。',
    ffmpegNone: '软件解码',
    openvinoAuto: 'OpenVINO 自动',
    cpuOnly: '仅 CPU',
    gpuPreferred: '优先 GPU',
    gpuHint: '这些设置会传给扫描、人脸、视觉、视频解码和语音识别任务。如果核显驱动不稳定，可以切到仅 CPU。',
    auto: '自动',
    gpu: 'GPU',
    cpu: 'CPU',
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
    modelManager: '模型管理',
    modelRoot: '模型目录',
    modelStatus: '状态',
    modelSize: '大小',
    modelPath: '路径',
    downloadModel: '下载',
    deleteModel: '删除缓存',
    downloadRecommended: '下载推荐模型',
    modelReady: '已就绪',
    modelMissing: '缺失',
    modelNeedsUrl: '需要 URL 环境变量',
    modelRuntimeCache: '运行时缓存',
    modelFile: '文件模型',
    modelHint: '模型不会打进 Docker 镜像，会下载到 /models；容器升级后缓存仍然保留。',
    deleteModelConfirm: '从 /models 删除这个模型缓存？',
    workflowConfirm: '这会连续运行多个任务，继续？',
    libraryHelp: '媒体库页是清单搜索结果页：在上方选择来源，可以按人物、关键词、路径、hash、人脸组、场景标签搜索。',
    libraryQuickSearch: '快捷搜索',
    rebuildIndex: '重建索引',
    rebuildSimilarity: '重建相似索引',
    mediaBrowser: '媒体浏览',
    randomMedia: '随机媒体',
    randomize: '随机刷新',
    tagGraphHelp: '经常一起出现的标签会连线。点击节点或连线可以按标签查媒体。',
    tagGraphFocusHelp: '点击节点聚焦，拖动节点整理图谱；点击连线会搜索同时包含两个标签的媒体。',
    selectedTag: '选中标签',
    connectedTags: '关联标签',
    clearFocus: '清除聚焦',
    showMedia: '查看媒体',
    tagGraphEmpty: '还没有标签图谱。先重建索引并同步视觉标签。',
    refreshGraph: '刷新图谱',
    relatedTags: '关联标签',
    transcript: '转写文字',
    noTranscript: '还没有转写内容',
    mediaSearch: '搜索媒体、标签、作者',
    allMedia: '全部媒体',
    photosOnly: '照片',
    videosOnly: '视频',
    openMedia: '打开',
    mediaDetail: '媒体详情',
    originalName: '原始文件名',
    sourceOriginalPath: '最初来源路径',
    indexedName: '库内文件名',
    filePath: '文件路径',
    tags: '标签',
    tagCorrect: '正确',
    tagWrong: '错误',
    tagFeedbackSaved: '反馈已保存',
    trainVisionCalibrator: '训练校准器',
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
      'workflow-full-library': '全量智能整理',
      'workflow-transcribe-sample': '语音样本',
      'model-pull-recommended': '下载推荐模型',
      'index-metadata': '重建索引',
      'index-similarity': '相似索引',
      'transcribe-sample': '语音样本',
      transcribe: '语音转写',
      scan: '扫描清单',
      'analyze-filenames': '分析文件名',
      'classify-keywords': '关键词归类',
      'normalize-organized': '规范目录',
      'refresh-state': '刷新统计',
      'extract-frames-sample': '抽帧样本',
      'extract-frames-retry-failed': '重试抽帧失败',
      'face-setup': '检查人脸环境',
      'vision-scan-sample': '视觉样本',
      'vision-scan-strong': '视觉强扫',
      'index-vision': '同步视觉索引',
      'train-vision-calibrator': '训练校准器',
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
      'model-pull-openclip-vit-l': '下载 OpenCLIP ViT-L',
      'model-pull-openclip-vit-h': '下载 OpenCLIP ViT-H',
      'model-pull-insightface-buffalo-l': '下载 InsightFace',
      'model-pull-faster-whisper-small': '下载 Whisper Small',
      'model-pull-sensevoice-small-gguf': '下载 SenseVoice GGUF',
      'model-pull-custom-detector-onnx': '下载自定义检测模型',
    },
    commandHelp: {
      'workflow-new-downloads': '新文件首选：扫描、分析、关键词归类、执行移动、刷新统计。',
      'workflow-review-cleanup': '重新整理 Unknown/NeedsManualCheck，并做精确去重。',
      'workflow-face-balanced': '重新抽帧、人脸扫描、保守聚类，生成新的人脸计划。',
      'workflow-vision-plan': '本地识别画面场景/标签，只生成预览计划。',
      'workflow-full-library': '完整跑扫描、整理、抽帧、人脸、场景、去重、转写和索引。',
      'workflow-transcribe-sample': '抽样转写视频语音，并把文字导入搜索。',
      'model-pull-recommended': '把默认视觉、人脸、语音模型下载到 /models。',
      'index-metadata': '把已整理文件和清单导入 SQLite 虚拟媒体库。',
      'index-similarity': '生成精确重复、图片感知 hash、视频关键帧相似组。',
      'transcribe-sample': '最多转写 5 个还没有文字的视频。',
      transcribe: '继续转写更多还没有文字的视频。',
      scan: '读取来源目录，生成 manifest_all.csv 和 move_plan.csv；本身不移动。',
      'analyze-filenames': '挖掘文件名里的人名、关键词、噪声词。',
      'classify-keywords': '把明显的 Unknown 文件移动到关键词分类。',
      'normalize-organized': '整理已有演员目录，把不靠谱的人名移回 review。',
      'refresh-state': '重新统计首页数字。',
      'extract-frames-sample': '只抽一小批缩略图/视频帧，供测试。',
      'extract-frames-retry-failed': '重新处理 frame_errors.csv 里的失败项。',
      'face-setup': '检查人脸/视觉依赖是否可用。',
      'vision-scan-sample': '只对小样本跑场景识别。',
      'vision-scan-strong': '默认只用更强 OpenCLIP 模型复扫低置信媒体。',
      'index-vision': '把 vision_labels.csv 和 frame_index.csv 导入标签和时间轴。',
      'train-vision-calibrator': '根据你手动确认/排除的标签训练轻量校准器。',
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
      'model-pull-openclip-vit-l': '下载/缓存默认 OpenCLIP 视觉模型。',
      'model-pull-openclip-vit-h': '下载/缓存更强的 OpenCLIP 模型。',
      'model-pull-insightface-buffalo-l': '下载/缓存 InsightFace buffalo_l 人脸模型。',
      'model-pull-faster-whisper-small': '下载/缓存 faster-whisper small 回退模型。',
      'model-pull-sensevoice-small-gguf': '从 SENSEVOICE_GGUF_URL 下载 SenseVoice GGUF 文件。',
      'model-pull-custom-detector-onnx': '从 CUSTOM_DETECTOR_ONNX_URL 下载可选自定义检测模型。',
    },
  },
};

const commands = [
  ['workflow-full-library', 'Full Library', Play, 'Run the full resumable pipeline'],
  ['workflow-new-downloads', 'New Downloads', Play, 'Recommended: scan, analyze, classify, apply, refresh'],
  ['workflow-review-cleanup', 'Review Cleanup', Archive, 'Recommended: normalize, classify review, dedupe, refresh'],
  ['workflow-face-balanced', 'Rebuild Faces', Users, 'Recommended: full frames, face scan, balanced cluster, report, plan'],
  ['workflow-vision-plan', 'Scene Plan', Camera, 'Recommended: full frames, OpenCLIP labels, dry-run vision plan'],
  ['workflow-transcribe-sample', 'Speech Sample', Mic, 'Transcribe a small local video sample'],
  ['index-metadata', 'Rebuild Index', Database, 'Import organized files into the virtual media library'],
  ['index-similarity', 'Similarity Index', Archive, 'Build duplicate and similarity groups'],
  ['transcribe-sample', 'Speech Sample', Mic, 'Transcribe up to 5 videos'],
  ['transcribe', 'Transcribe', Mic, 'Transcribe more videos'],
  ['scan', 'Scan', Search, 'Rebuild manifests and move plan'],
  ['analyze-filenames', 'Analyze Names', FileSearch, 'Mine actor and keyword signals'],
  ['classify-keywords', 'Keywords', Tags, 'Move clear Unknown items into keyword buckets'],
  ['normalize-organized', 'Normalize', Archive, 'Flatten actor folders and move weak actor names to review'],
  ['refresh-state', 'Refresh State', RefreshCw, 'Recount library state snapshot'],
  ['extract-frames-sample', 'Frames Sample', Camera, 'Cache frames for a small sample'],
  ['extract-frames-retry-failed', 'Retry Frames', Camera, 'Retry failed frame extraction rows'],
  ['face-setup', 'Face Setup', ScanFace, 'Show local face dependency status'],
  ['vision-scan-sample', 'Vision Sample', Camera, 'Run OpenCLIP sample when CLIP image is used'],
  ['vision-scan-strong', 'Vision Strong Rescan', Camera, 'Rescan low-confidence media with the strong model'],
  ['index-vision', 'Sync Vision', Camera, 'Import vision outputs into media tags and timelines'],
  ['train-vision-calibrator', 'Train Calibrator', Tags, 'Train lightweight tag calibrators from manual feedback'],
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
  ['tagGraph', 'tagGraph', Share2],
  ['randomFlow', 'randomFlow', Shuffle],
  ['models', 'models', HardDrive],
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

function Stat({ label, value, icon: Icon, tone = 'blue', sub = '' }) {
  return <div className={`stat ${tone}`}><div className="statIcon"><Icon size={24} /></div><div><div className="statValue">{value ?? 0}</div><div className="statLabel">{label}</div>{sub && <div className="statSub">{sub}</div>}</div></div>;
}

function JobBadge({ status }) {
  const Icon = status === 'done' ? CheckCircle2 : status === 'failed' ? XCircle : Activity;
  return <span className={`badge ${status}`}><Icon size={13} />{status}</span>;
}

function Empty({ label }) {
  return <div className="empty">{label}</div>;
}

function displayVersion(version) {
  return version?.version || 'v1.0.0';
}

function buildLabel(version, t) {
  const build = version?.build_commit || '';
  if (!build || build === 'dev') return '';
  return `${t.build} ${String(build).slice(0, 7)}`;
}

function prettyNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString() : '0';
}

function prettyBytes(value) {
  let size = Number(value || 0);
  if (!Number.isFinite(size) || size <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size >= 10 || index === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[index]}`;
}

function estimatedMediaTotal(summary, mediaResults) {
  const top = summary?.top || {};
  if (Number(mediaResults?.total || 0) > 0) return Number(mediaResults.total);
  const known = Number(top.actors || 0) + Number(top.keywords || 0) + Number(top.unknown || 0) + Number(top.duplicates || 0);
  return known || 0;
}

function initialAspect(item) {
  const width = Number(item?.width || 0);
  const height = Number(item?.height || 0);
  if (width > 0 && height > 0) return Math.max(0.38, Math.min(3.2, width / height));
  return item?.media_type === 'video' ? 16 / 9 : 4 / 5;
}

function MediaThumbImage({ item, className = 'mediaThumb', label = '' }) {
  const [aspect, setAspect] = useState(initialAspect(item));
  const badge = label || (item.media_type === 'video' ? 'VID' : 'IMG');
  return (
    <div className={className} style={{ '--thumb-ratio': String(aspect) }}>
      <img
        src={`/api/media/${item.id}/thumbnail`}
        alt={item.filename}
        loading="lazy"
        onLoad={event => {
          const img = event.currentTarget;
          if (img.naturalWidth && img.naturalHeight) {
            setAspect(Math.max(0.38, Math.min(3.2, img.naturalWidth / img.naturalHeight)));
          }
        }}
        onError={event => { event.currentTarget.style.display = 'none'; }}
      />
      <span>{badge}</span>
    </div>
  );
}

function LoginScreen({ login, error, theme, setTheme, t, version }) {
  const [password, setPassword] = useState('');
  return (
    <main className="loginShell">
      <section className="loginPanel">
        <div className="brand"><Bot size={22} /><div><strong>{t.app}</strong><span>{t.manager}</span><small>{displayVersion(version)} {buildLabel(version, t)}</small></div></div>
        <h1>{t.login}</h1>
        <p>{t.privacyCopy}</p>
        {error && <div className="alert">{error}</div>}
        <form className="loginForm" onSubmit={event => { event.preventDefault(); login(password); }}>
          <label>{t.password}<input type="password" value={password} onChange={event => setPassword(event.target.value)} autoFocus /></label>
          <button type="submit"><Save size={16} />{t.unlock}</button>
        </form>
        <button className="iconButton" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Theme">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
      </section>
    </main>
  );
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
  const [randomResults, setRandomResults] = useState({ total: 0, items: [] });
  const [similarityResults, setSimilarityResults] = useState({ groups: [] });
  const [tagGraph, setTagGraph] = useState({ nodes: [], edges: [] });
  const [authors, setAuthors] = useState([]);
  const [faces, setFaces] = useState([]);
  const [faceSuggestions, setFaceSuggestions] = useState([]);
  const [settings, setSettings] = useState(null);
  const [models, setModels] = useState({ root: '/models', models: [] });
  const [monitor, setMonitor] = useState(null);
  const [directories, setDirectories] = useState([]);
  const [browsePath, setBrowsePath] = useState('/media');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [auth, setAuth] = useState({ enabled: false, authenticated: true, local_only: true });
  const [version, setVersion] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [language, setLanguage] = useState(() => localStorage.getItem('language') || 'zh-CN');
  const t = i18n[language] || i18n['zh-CN'];

  async function refresh() {
    const [s, j, a, f, suggestions, cfg, mon, modelCatalog, ver] = await Promise.all([
      api('/api/summary'),
      api('/api/jobs'),
      api('/api/authors').catch(() => []),
      api('/api/face-groups').catch(() => []),
      api('/api/face-merge-suggestions').catch(() => []),
      api('/api/settings').catch(() => null),
      api('/api/monitor').catch(() => null),
      api('/api/models').catch(() => ({ root: '/models', models: [] })),
      api('/api/version').catch(() => null),
    ]);
    setSummary(s);
    setJobs(j);
    setAuthors(a);
    setFaces(f);
    setFaceSuggestions(suggestions);
    setMonitor(mon);
    setModels(modelCatalog);
    if (ver) setVersion(ver);
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
    api('/api/auth/status').then(status => {
      setAuth(status);
      api('/api/version').then(setVersion).catch(() => {});
      if (status.authenticated) {
        refresh().catch(exc => setError(exc.message));
        loadMedia().catch(() => {});
        loadRandomMedia().catch(() => {});
        loadTagGraph().catch(() => {});
        loadSimilarity().catch(() => {});
        loadModels().catch(() => {});
      }
    }).catch(exc => setError(exc.message));
    const id = setInterval(() => refresh().catch(() => {}), 4000);
    return () => clearInterval(id);
  }, []);

  async function login(password) {
    setError('');
    await api('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
    const status = await api('/api/auth/status');
    setAuth(status);
    await refresh();
    await loadMedia();
    await loadRandomMedia();
    await loadTagGraph();
    await loadSimilarity();
    await loadModels();
  }

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

  async function cancelJob(id) {
    const ok = window.confirm(language === 'zh-CN' ? '停止当前任务？已写入的缓存会保留，下次可以继续。' : 'Stop this job? Completed cache files will be kept and can be resumed later.');
    if (!ok) return;
    await api(`/api/jobs/${id}/cancel`, { method: 'POST' });
    await refresh();
    await openJob(id);
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
      randomize: params.randomize ? 'true' : 'false',
      limit: String(params.limit || 80),
      offset: String(params.offset || 0),
    });
    const data = await api(`/api/media?${search.toString()}`);
    setMediaResults(data);
    return data;
  }

  async function loadRandomMedia(params = {}) {
    const search = new URLSearchParams({
      q: params.q || '',
      media_type: params.media_type || 'all',
      tag: params.tag || '',
      author: params.author || '',
      randomize: 'true',
      limit: String(params.limit || 80),
      offset: '0',
    });
    const data = await api(`/api/media?${search.toString()}`);
    setRandomResults(data);
    return data;
  }

  async function loadTagGraph(params = {}) {
    const search = new URLSearchParams({
      limit_nodes: String(params.limit_nodes || 90),
      limit_edges: String(params.limit_edges || 220),
      min_edge: String(params.min_edge || 2),
    });
    const data = await api(`/api/tags/graph?${search.toString()}`);
    setTagGraph(data);
    return data;
  }

  async function loadSimilarity() {
    const data = await api('/api/media/similarity-groups?limit=80');
    setSimilarityResults(data);
    return data;
  }

  async function loadModels() {
    const data = await api('/api/models');
    setModels(data);
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

  async function pullModel(modelId) {
    const command = `model-pull-${modelId}`;
    await start(command);
  }

  async function deleteModel(modelId) {
    const ok = window.confirm(t.deleteModelConfirm);
    if (!ok) return;
    setError('');
    try {
      await api(`/api/models/${encodeURIComponent(modelId)}`, { method: 'DELETE' });
      await loadModels();
      setMessage(t.modelMissing);
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

  if (auth.enabled && !auth.authenticated) {
    return <LoginScreen login={login} error={error} theme={theme} setTheme={setTheme} t={t} version={version} />;
  }

  return (
    <main>
      <aside>
        <div className="brand"><div className="brandMark"><Bot size={20} /></div><div><strong>{t.app}</strong><span>{t.manager}</span><small title={buildLabel(version, t)}>{displayVersion(version)}</small></div></div>
        <nav>{nav.map(([id, labelKey, Icon]) => <button className={active === id ? 'active' : ''} key={id} onClick={() => setActive(id)}><Icon size={16} /> {t[labelKey]}</button>)}</nav>
      </aside>

      <section className="content">
        <header>
          <div className="pageTitle"><h1>{t.title}</h1><p>{summary?.root || '/media'} {summary?.output_root && summary.output_root !== summary.root ? `-> ${summary.output_root}` : ''}</p></div>
          <div className="headerActions">
            <form className="searchForm" onSubmit={runSearch}>
              <select value={source} onChange={event => setSource(event.target.value)} title="Search source">
                {['all', 'manifest', 'move_plan', 'applied', 'filename_words', 'filename_analysis', 'face_groups', 'face_merge_suggestions', 'vision_labels', 'vision_move_plan', 'organized_duplicates'].map(item => <option value={item} key={item}>{t[item] || item}</option>)}
              </select>
              <input value={query} onChange={event => setQuery(event.target.value)} placeholder={t.searchPlaceholder} />
              <button type="submit" title="Search"><Search size={16} /></button>
            </form>
            <button className="iconButton" title={t.recentLogs} onClick={() => setActive('logs')}><Bell size={18} /></button>
            <button className="iconButton" title={t.privacyLocked}><LockKeyhole size={18} /></button>
            <button className="iconButton" title={t.viewSwitcher} onClick={() => setActive('library')}><Grid3X3 size={18} /></button>
            <button className="iconButton" onClick={() => setLanguage(language === 'zh-CN' ? 'en' : 'zh-CN')} title={t.language}><Languages size={18} /></button>
            <button className="iconButton" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Theme">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
            <button className="iconButton" onClick={refresh} title="Refresh"><RefreshCw size={18} /></button>
          </div>
        </header>

        {error && <div className="alert">{error}</div>}
        {message && <div className="notice">{message}</div>}

        {active === 'dashboard' && (
          <>
            <DashboardPanel
              summary={summary}
              jobs={jobs}
              mediaResults={mediaResults}
              tagGraph={tagGraph}
              loadMedia={loadMedia}
              setActive={setActive}
              t={t}
            />
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

        {active === 'jobs' && <section className="twoCol jobsLayout"><JobsPanel jobs={jobs} openJob={openJob} t={t} /><LogPanel selectedJob={selectedJob} jobLog={jobLog} start={start} cancelJob={cancelJob} setActive={setActive} t={t} /></section>}
        {active === 'library' && <LibraryPanel results={results} mediaResults={mediaResults} similarityResults={similarityResults} loadMedia={loadMedia} loadSimilarity={loadSimilarity} start={start} performSearch={performSearch} setQuery={setQuery} setSource={setSource} t={t} />}
        {active === 'tagGraph' && <TagGraphPanel graph={tagGraph} loadTagGraph={loadTagGraph} loadMedia={loadMedia} setActive={setActive} t={t} />}
        {active === 'randomFlow' && <RandomFlowPanel mediaResults={randomResults} loadRandomMedia={loadRandomMedia} t={t} />}
        {active === 'models' && <ModelsPanel catalog={models} pullModel={pullModel} deleteModel={deleteModel} start={start} busy={busy || hasRunning} t={t} />}
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

function DashboardPanel({ summary, jobs, mediaResults, tagGraph, loadMedia, setActive, t }) {
  const top = summary?.top || {};
  const keywords = summary?.keywords || [];
  const actors = summary?.actors_sample || [];
  const runningJobs = jobs.filter(job => job.status === 'running' || job.status === 'queued');
  const items = (mediaResults.items || []).slice(0, 6);
  const mediaTotal = estimatedMediaTotal(summary, mediaResults);
  const stats = [
    [t.totalMedia, mediaTotal, FolderOpen, 'blue', `${t.videos} ${prettyNumber(mediaResults.video_total || 0)} / ${t.photos} ${prettyNumber(mediaResults.photo_total || 0)}`],
    [t.totalTags, keywords.length || top.keywords, Tags, 'purple', `${t.keywords} ${prettyNumber(top.keywords || 0)}`],
    [t.totalAuthors, actors.length || top.actors, Users, 'green', `${t.actors} ${prettyNumber(top.actors || 0)}`],
    [t.faces, top.faces || summary?.vision?.face_group_rows || 0, ScanFace, 'orange', `${t.faceRows} ${prettyNumber(summary?.vision?.face_index_rows || 0)}`],
    [t.taskRunning, runningJobs.length, CheckCircle2, 'blue', `${t.jobs} ${prettyNumber(jobs.length)}`],
  ];
  return (
    <>
      <section className="dashboardStats">
        {stats.map(([label, value, Icon, tone, sub]) => <Stat key={label} label={label} value={prettyNumber(value)} icon={Icon} tone={tone} sub={sub} />)}
      </section>
      <section className="dashboardMain">
        <DashboardTagGraph graph={tagGraph} keywords={keywords} loadMedia={loadMedia} setActive={setActive} t={t} />
        <RecentMediaPanel items={items} total={mediaResults.total || items.length} setActive={setActive} t={t} />
      </section>
      <section className="dashboardBottom">
        <DashboardJobs jobs={jobs} setActive={setActive} t={t} />
        <StoragePanel summary={summary} mediaTotal={mediaTotal} t={t} />
      </section>
    </>
  );
}

function DashboardTagGraph({ graph, keywords, loadMedia, setActive, t }) {
  const sourceNodes = (graph.nodes || []).length ? graph.nodes : keywords.map(item => ({ tag: item.name, media_count: item.files, category: t.keywords }));
  const topNodes = sourceNodes.slice(0, 8);
  const center = topNodes[0] || { tag: t.tagGraph, media_count: 0 };
  const satellites = topNodes.slice(1, 8);
  const colors = ['violet', 'blue', 'green', 'orange', 'pink', 'cyan', 'amber'];
  function open(tag) {
    if (!tag) return;
    loadMedia({ tag, limit: 100 });
    setActive('library');
  }
  return (
    <section className="panel dashboardGraphPanel">
      <div className="panelHead"><h2>{t.tagGraph}</h2><button className="softLink" onClick={() => setActive('tagGraph')}>{t.viewAll}</button></div>
      <div className="orbitGraph">
        <button className="orbitNode orbitCenter" onClick={() => open(center.tag)}>
          <strong>{center.tag}</strong>
          <span>{prettyNumber(center.media_count)}</span>
        </button>
        {satellites.map((node, index) => {
          const angle = (index / Math.max(1, satellites.length)) * Math.PI * 2 - Math.PI / 2;
          const x = 50 + Math.cos(angle) * 34;
          const y = 50 + Math.sin(angle) * 31;
          return (
            <button
              className={`orbitNode ${colors[index % colors.length]}`}
              key={node.tag}
              style={{ left: `${x}%`, top: `${y}%` }}
              onClick={() => open(node.tag)}
            >
              <strong>{node.tag}</strong>
              <span>{prettyNumber(node.media_count)}</span>
            </button>
          );
        })}
      </div>
      <div className="graphLegend">
        {(keywords || []).slice(0, 5).map((item, index) => <span key={item.name}><i className={colors[index % colors.length]} />{item.name}</span>)}
      </div>
    </section>
  );
}

function RecentMediaPanel({ items, total, setActive, t }) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  async function open(item) {
    setSelected(item);
    setDetail(await api(`/api/media/${item.id}`));
  }
  return (
    <section className="panel recentPanel">
      <div className="panelHead"><h2>{t.recentAdded}</h2><button className="softLink" onClick={() => setActive('library')}>{t.viewAll}</button></div>
      {!items.length ? <Empty label={t.recentEmpty} /> : <div className="recentGrid">{items.map(item => <RecentMediaCard item={item} key={item.id} open={open} />)}</div>}
      <div className="panelFoot">{prettyNumber(total)} {t.media}</div>
      {selected && <MediaViewer item={selected} detail={detail} close={() => { setSelected(null); setDetail(null); }} t={t} />}
    </section>
  );
}

function RecentMediaCard({ item, open }) {
  return (
    <button className="recentCard" onClick={() => open(item)}>
      <MediaThumbImage item={item} className="recentThumb" />
      <div className="recentMeta">
        <span>{item.media_type === 'video' ? <Film size={14} /> : <ImageIcon size={14} />}{item.media_type}</span>
        <strong>{item.author || item.scene || item.filename}</strong>
        <small>{item.duration ? formatSeconds(item.duration) : item.quality || ''}</small>
      </div>
    </button>
  );
}

function DashboardJobs({ jobs, setActive, t }) {
  const rows = jobs.slice(0, 4);
  return (
    <section className="panel taskPanel">
      <div className="panelHead"><h2>{t.taskList}</h2><button className="softLink" onClick={() => setActive('jobs')}>{t.viewAllTasks}</button></div>
      {!rows.length ? <Empty label={t.noRows} /> : <div className="taskRows">{rows.map(job => {
        const progress = job.status === 'done' ? 100 : job.status === 'running' ? 66 : job.status === 'queued' ? 28 : 0;
        return (
          <button className="taskRow" key={job.id} onClick={() => setActive('jobs')}>
            <span>{job.command}</span>
            <strong>{progress}%</strong>
            <i><b style={{ width: `${progress}%` }} /></i>
            <em>{job.status}</em>
          </button>
        );
      })}</div>}
    </section>
  );
}

function StoragePanel({ summary, mediaTotal, t }) {
  const top = summary?.top || {};
  const videos = Number(summary?.media_types?.video || 0);
  const photos = Number(summary?.media_types?.photo || 0);
  const other = Math.max(0, Number(mediaTotal || 0) - videos - photos);
  const used = Math.max(1, videos + photos + other || mediaTotal || 1);
  const videoPct = Math.max(6, Math.round((videos / used) * 100));
  const photoPct = Math.max(6, Math.round((photos / used) * 100));
  return (
    <section className="panel storagePanel">
      <div className="panelHead"><h2>{t.storageSpace}</h2><span>{t.localOnly}</span></div>
      <div className="storageBody">
        <div className="storageRing" style={{ '--video': `${videoPct}%`, '--photo': `${photoPct}%` }}><HardDrive size={24} /><strong>{prettyNumber(mediaTotal)}</strong><span>{t.usedSpace}</span></div>
        <div className="storageList">
          <div><i className="violet" /><span>{t.videoFiles}</span><strong>{prettyNumber(videos)}</strong></div>
          <div><i className="pink" /><span>{t.imageFiles}</span><strong>{prettyNumber(photos)}</strong></div>
          <div><i className="blue" /><span>{t.otherFiles}</span><strong>{prettyNumber(other || top.unknown || 0)}</strong></div>
          <div><i className="green" /><span>{t.availableSpace}</span><strong>{prettyNumber(top.duplicates || 0)}</strong></div>
        </div>
      </div>
    </section>
  );
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
    ['workflow-full-library', t.commandNames?.['workflow-full-library'] || 'Full Library', t.commandHelp?.['workflow-full-library'] || '', Play],
    ['workflow-new-downloads', t.newDownloadsWorkflow, t.newDownloadsHint, Search],
    ['workflow-review-cleanup', t.reviewCleanupWorkflow, t.reviewCleanupHint, Archive],
    ['workflow-face-balanced', t.faceWorkflow, t.faceWorkflowHint, Users],
    ['workflow-vision-plan', t.visionWorkflow, t.visionWorkflowHint, Camera],
    ['workflow-transcribe-sample', t.transcribeWorkflow, t.transcribeWorkflowHint, Mic],
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
    [t.commonCommands, ['workflow-full-library', 'workflow-new-downloads', 'workflow-review-cleanup', 'scan', 'apply']],
    [t.faceCommands, ['workflow-face-balanced', 'extract-frames-retry-failed', 'face-scan-sample', 'face-cluster-balanced', 'face-cluster-report', 'apply-face-groups-dry-run', 'apply-face-groups']],
    [t.visionCommands, ['workflow-vision-plan', 'vision-scan-sample', 'vision-scan-strong', 'index-vision', 'train-vision-calibrator', 'apply-vision-labels-dry-run', 'apply-vision-labels']],
    [t.transcriptCommands, ['workflow-transcribe-sample', 'transcribe-sample', 'transcribe']],
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
  return <div className="panel"><div className="panelHead"><h2>{t.visionPipeline}</h2><span>{t.localOnly}</span></div><div className="list">{['frame_index_rows', 'face_index_rows', 'face_group_rows', 'vision_label_rows', 'vision_embedding_rows', 'face_move_plan_rows'].map(key => <div className="row" key={key}><span>{key.replace('_rows', '.csv')}</span><strong>{vision[key] || 0}</strong></div>)}</div></div>;
}

function SourcePanel({ leftovers, title }) {
  return <div className="panel"><div className="panelHead"><h2>{title}</h2><span>{Object.values(leftovers).reduce((a, b) => a + b, 0)}</span></div><div className="list">{Object.entries(leftovers).map(([name, files]) => <div className="row" key={name}><span>{name}</span><strong>{files}</strong></div>)}</div></div>;
}

function jobPercent(job) {
  const value = Number(job.progress || 0);
  if (job.status === 'done') return 100;
  return Math.max(0, Math.min(100, value));
}

function JobsPanel({ jobs, openJob, t }) {
  return <div className="panel"><div className="panelHead"><h2>{t.jobs}</h2><span>{jobs.length}</span></div><div className="jobs">{jobs.map(job => {
    const pct = jobPercent(job);
    const processed = Number(job.processed || 0);
    const total = Number(job.total || 0);
    return (
      <button className="job" key={job.id} onClick={() => openJob(job.id)}>
        <div className="jobMain">
          <strong>#{job.id} {t.commandNames?.[job.command] || job.command}</strong>
          <p>{job.stage || job.message || job.created_at}</p>
          {job.current_item && <small>{job.current_item}</small>}
          <i className="jobProgress"><b style={{ width: `${pct}%` }} /></i>
          <small>{pct}% {total ? `${processed}/${total}` : ''} {Number(job.failed_count || 0) ? ` failed ${job.failed_count}` : ''}</small>
        </div>
        <JobBadge status={job.status} />
      </button>
    );
  })}</div></div>;
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

function LogPanel({ selectedJob, jobLog, start, cancelJob, setActive, t }) {
  const next = selectedJob ? jobNextStep(selectedJob.command, t) : '';
  const actions = selectedJob ? jobNextActions(selectedJob.command, t, start, setActive) : [];
  const canStop = selectedJob && ['queued', 'running'].includes(selectedJob.status);
  const canResume = selectedJob && ['cancelled', 'failed'].includes(selectedJob.status);
  const pct = selectedJob ? jobPercent(selectedJob) : 0;
  return <div className="panel"><div className="panelHead"><h2>{selectedJob ? `Job #${selectedJob.id}` : t.jobLog}</h2><span>{selectedJob?.status || t.selectJob}</span></div>{!selectedJob ? <Empty label={t.selectJobHint} /> : <div className="logBlock">
    <div className="jobDetailHero">
      <strong>{pct}%</strong>
      <i className="jobProgress"><b style={{ width: `${pct}%` }} /></i>
      <span>{selectedJob.stage || selectedJob.message || '-'}</span>
    </div>
    <div className="nextActions">
      {canStop && <button onClick={() => cancelJob(selectedJob.id)}><Archive size={15} />{t.stopJob || 'Stop'}</button>}
      {canResume && <button onClick={() => start(selectedJob.command)}><Play size={15} />{t.resumeJob || 'Resume'}</button>}
      <button onClick={() => start('extract-frames-retry-failed')}><RefreshCw size={15} />{t.commandNames?.['extract-frames-retry-failed'] || 'Retry Frames'}</button>
    </div>
    <div className="list">
      <div className="row"><span>{t.command}</span><strong>{selectedJob.command}</strong></div>
      <div className="row"><span>stage</span><strong>{selectedJob.stage || '-'}</strong></div>
      <div className="row"><span>processed</span><strong>{selectedJob.processed || 0}/{selectedJob.total || 0}</strong></div>
      <div className="row"><span>current</span><strong>{selectedJob.current_item || '-'}</strong></div>
      <div className="row"><span>failed/skipped</span><strong>{selectedJob.failed_count || 0}/{selectedJob.skipped_count || 0}</strong></div>
      <div className="row"><span>heartbeat</span><strong>{selectedJob.heartbeat_at || '-'}</strong></div>
      <div className="row"><span>{t.started}</span><strong>{selectedJob.started_at || '-'}</strong></div>
      <div className="row"><span>{t.finished}</span><strong>{selectedJob.finished_at || '-'}</strong></div>
    </div>
    {next && <div className="hintBox"><strong>{t.jobNextStep}</strong><span>{next}</span>{actions.length > 0 && <div className="nextActions">{actions.map(([label, action]) => <button key={label} onClick={action}><Play size={15} />{label}</button>)}</div>}</div>}
    <h3>stdout</h3><pre>{jobLog?.stdout || '(empty)'}</pre><h3>stderr</h3><pre>{jobLog?.stderr || '(empty)'}</pre></div>}</div>;
}

function TagGraphPanel({ graph, loadTagGraph, loadMedia, setActive, t }) {
  const [minEdge, setMinEdge] = useState(2);
  const [focusedTag, setFocusedTag] = useState('');
  const [draggingTag, setDraggingTag] = useState('');
  const [manualPositions, setManualPositions] = useState({});
  const [hoverPoint, setHoverPoint] = useState(null);
  const [zoom, setZoom] = useState(1);
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const topNodes = nodes.slice(0, 48);
  const maxCount = Math.max(...topNodes.map(node => Number(node.media_count || 0)), 1);
  const positions = useMemo(() => new Map(topNodes.map((node, index) => {
    if (manualPositions[node.tag]) return [node.tag, manualPositions[node.tag]];
    const angle = (index / Math.max(1, topNodes.length)) * Math.PI * 2;
    const radius = 16 + Math.sqrt(index + 1) * 5.8;
    return [node.tag, {
      x: Math.max(6, Math.min(94, 50 + Math.cos(angle) * radius)),
      y: Math.max(8, Math.min(92, 50 + Math.sin(angle) * radius)),
    }];
  })), [topNodes, manualPositions]);
  const neighborMap = useMemo(() => {
    const map = new Map();
    edges.forEach(edge => {
      if (!map.has(edge.source)) map.set(edge.source, []);
      if (!map.has(edge.target)) map.set(edge.target, []);
      map.get(edge.source).push({ tag: edge.target, weight: edge.weight, edge });
      map.get(edge.target).push({ tag: edge.source, weight: edge.weight, edge });
    });
    for (const values of map.values()) values.sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0));
    return map;
  }, [edges]);
  const focusedNeighbors = focusedTag ? (neighborMap.get(focusedTag) || []) : [];
  function openTag(tag, secondTag = '') {
    loadMedia({ tag: secondTag ? `${tag},${secondTag}` : tag, limit: 100 });
    setActive('library');
  }
  function svgPoint(event) {
    const rect = event.currentTarget.closest('svg').getBoundingClientRect();
    return {
      x: Math.max(4, Math.min(96, ((event.clientX - rect.left) / Math.max(1, rect.width)) * 100)),
      y: Math.max(6, Math.min(94, ((event.clientY - rect.top) / Math.max(1, rect.height)) * 100)),
    };
  }
  function displayPoint(point) {
    if (!hoverPoint || draggingTag) return point;
    const dx = hoverPoint.x - point.x;
    const dy = hoverPoint.y - point.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > 18) return point;
    const pull = (1 - distance / 18) * 2.8;
    return {
      x: Math.max(4, Math.min(96, point.x + (dx / Math.max(1, distance)) * pull)),
      y: Math.max(6, Math.min(94, point.y + (dy / Math.max(1, distance)) * pull)),
    };
  }
  function displayPositions() {
    const map = new Map();
    positions.forEach((point, tag) => map.set(tag, displayPoint(point)));
    return map;
  }
  function moveNode(event) {
    const point = svgPoint(event);
    setHoverPoint(point);
    if (!draggingTag) return;
    setManualPositions({ ...manualPositions, [draggingTag]: point });
  }
  function zoomGraph(event) {
    event.preventDefault();
    setZoom(value => Math.max(0.7, Math.min(1.55, value + (event.deltaY > 0 ? -0.08 : 0.08))));
  }
  function edgeIsFocused(edge) {
    return focusedTag && (edge.source === focusedTag || edge.target === focusedTag);
  }
  function nodeIsDimmed(tag) {
    if (!focusedTag || tag === focusedTag) return false;
    return !focusedNeighbors.some(item => item.tag === tag);
  }
  const drawnPositions = displayPositions();
  const viewSize = 100 / zoom;
  const viewOffset = (100 - viewSize) / 2;
  return (
    <>
      <section className="panel">
        <div className="panelHead"><h2>{t.tagGraph}</h2><div className="panelActions"><button className="iconButton mini" onClick={() => setZoom(value => Math.max(0.7, value - 0.12))}>-</button><button className="iconButton mini" onClick={() => setZoom(1)}>{Math.round(zoom * 100)}%</button><button className="iconButton mini" onClick={() => setZoom(value => Math.min(1.55, value + 0.12))}>+</button><select value={minEdge} onChange={event => setMinEdge(Number(event.target.value))}><option value="1">1+</option><option value="2">2+</option><option value="4">4+</option><option value="8">8+</option></select><button className="panelButton" onClick={() => loadTagGraph({ min_edge: minEdge })}><RefreshCw size={16} />{t.refreshGraph}</button></div><span>{nodes.length}</span></div>
        <div className="hintBox"><span>{t.tagGraphHelp} {t.tagGraphFocusHelp}</span></div>
        {!nodes.length ? <Empty label={t.tagGraphEmpty} /> : (
          <div className="graphLayout">
            <svg className="tagGraphCanvas" viewBox={`${viewOffset} ${viewOffset} ${viewSize} ${viewSize}`} role="img" onPointerMove={moveNode} onWheel={zoomGraph} onPointerUp={() => setDraggingTag('')} onPointerLeave={() => { setDraggingTag(''); setHoverPoint(null); }}>
              {edges.filter(edge => positions.has(edge.source) && positions.has(edge.target)).slice(0, 180).map(edge => {
                const left = drawnPositions.get(edge.source);
                const right = drawnPositions.get(edge.target);
                return <line className={edgeIsFocused(edge) ? 'isFocused' : focusedTag ? 'isDimmed' : ''} key={`${edge.source}-${edge.target}`} x1={left.x} y1={left.y} x2={right.x} y2={right.y} strokeWidth={Math.min(2.2, 0.25 + Number(edge.weight || 1) / 18)} onClick={() => openTag(edge.source, edge.target)} />;
              })}
              {topNodes.map(node => {
                const point = drawnPositions.get(node.tag);
                const size = 1.8 + (Number(node.media_count || 0) / maxCount) * 4.2;
                const classes = [focusedTag === node.tag ? 'isFocused' : '', nodeIsDimmed(node.tag) ? 'isDimmed' : ''].filter(Boolean).join(' ');
                return (
                  <g className={classes} key={node.tag} onClick={() => setFocusedTag(node.tag)} onDoubleClick={() => openTag(node.tag)} onPointerDown={event => { event.currentTarget.setPointerCapture?.(event.pointerId); setDraggingTag(node.tag); }}>
                    <circle cx={point.x} cy={point.y} r={size} />
                    <text x={point.x} y={point.y - size - 1.2}>{node.tag}</text>
                  </g>
                );
              })}
              {hoverPoint && <circle className="graphCursor" cx={hoverPoint.x} cy={hoverPoint.y} r={2.4 / zoom} />}
            </svg>
            <div className="tagNodeList">
              {focusedTag && (
                <div className="tagFocusCard">
                  <span>{t.selectedTag}</span>
                  <strong>{focusedTag}</strong>
                  <div className="focusActions">
                    <button onClick={() => openTag(focusedTag)}>{t.showMedia}</button>
                    <button onClick={() => setFocusedTag('')}>{t.clearFocus}</button>
                  </div>
                </div>
              )}
              {(focusedTag ? focusedNeighbors.map(item => ({ tag: item.tag, media_count: item.weight, category: t.connectedTags, pair: focusedTag })) : nodes.slice(0, 60)).map(node => <button className={focusedTag && node.tag === focusedTag ? 'isActive' : ''} key={`${node.category}-${node.tag}`} onClick={() => focusedTag && node.pair ? openTag(node.pair, node.tag) : setFocusedTag(node.tag)}><span>{node.category || t.tags}</span><strong>{node.tag}</strong><em>{node.media_count}</em></button>)}
            </div>
          </div>
        )}
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.relatedTags}</h2><span>{edges.length}</span></div>
        {!edges.length ? <Empty label={t.noRows} /> : <div className="edgeList">{edges.slice(0, 80).map(edge => <button key={`${edge.source}-${edge.target}`} onClick={() => openTag(edge.source, edge.target)}><strong>{edge.source}</strong><span>{edge.target}</span><em>{edge.weight}</em></button>)}</div>}
      </section>
    </>
  );
}

function RandomFlowPanel({ mediaResults, loadRandomMedia, t }) {
  const [filters, setFilters] = useState({ media_type: 'all', tag: '', author: '', q: '' });
  function run(event) {
    event?.preventDefault();
    loadRandomMedia(filters);
  }
  return (
    <section className="panel">
      <div className="panelHead"><h2>{t.randomFlow}</h2><button className="panelButton" onClick={run}><Shuffle size={16} />{t.randomize}</button><span>{mediaResults.total || 0}</span></div>
      <form className="mediaSearchBar randomBar" onSubmit={run}>
        <select value={filters.media_type} onChange={event => setFilters({ ...filters, media_type: event.target.value })}>
          <option value="all">{t.allMedia}</option>
          <option value="photo">{t.photosOnly}</option>
          <option value="video">{t.videosOnly}</option>
        </select>
        <input value={filters.q} onChange={event => setFilters({ ...filters, q: event.target.value })} placeholder={t.mediaSearch} />
        <input value={filters.tag} onChange={event => setFilters({ ...filters, tag: event.target.value })} placeholder={t.tags} />
        <input value={filters.author} onChange={event => setFilters({ ...filters, author: event.target.value })} placeholder={t.authorName} />
        <button type="submit"><Shuffle size={16} />{t.randomize}</button>
      </form>
      <MediaGrid items={mediaResults.items || []} t={t} />
    </section>
  );
}

function LibraryPanel({ results, mediaResults, similarityResults, loadMedia, loadSimilarity, start, performSearch, setQuery, setSource, t }) {
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
      <SimilarityPanel groups={similarityResults.groups || []} start={start} refresh={loadSimilarity} t={t} />
      <section className="panel">
        <div className="panelHead"><h2>{t.library}</h2><span>{t.libraryQuickSearch}</span></div>
        <div className="hintBox"><span>{t.libraryHelp}</span></div>
        <div className="quickGrid">{quick.map(([src, value]) => <button key={`${src}-${value}`} onClick={() => quickSearch(src, value)}>{src}: {value}</button>)}</div>
      </section>
      <section className="panel"><div className="panelHead"><h2>{t.searchResults}</h2><span>{results.length} rows</span></div><ResultsTable rows={results} t={t} /></section>
    </>
  );
}

function SimilarityPanel({ groups, start, refresh, t }) {
  return (
    <section className="panel">
      <div className="panelHead"><h2>{t.similarityGroups}</h2><div className="panelActions"><button className="panelButton" onClick={() => start('index-similarity')}><Archive size={16} />{t.rebuildSimilarity}</button><button className="panelButton" onClick={refresh}><RefreshCw size={16} />{t.refreshState || t.ready}</button></div><span>{groups.length}</span></div>
      {!groups.length ? <Empty label={t.noRows} /> : <div className="similarityGrid">{groups.map(group => <SimilarityCard group={group} key={group.id} />)}</div>}
    </section>
  );
}

function SimilarityCard({ group }) {
  return (
    <article className="similarityCard">
      <div className="similarityHead"><strong>{group.kind}</strong><span>{group.members}</span></div>
      <div className="similarityItems">
        {(group.items || []).slice(0, 4).map(item => (
          <div className="similarityItem" key={item.id}>
            <img src={`/api/media/${item.id}/thumbnail`} alt={item.filename} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} />
            <div><strong>{item.role}</strong><span>{item.filename}</span></div>
          </div>
        ))}
      </div>
    </article>
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
            <MediaThumbImage item={item} />
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
  const [feedbackMessage, setFeedbackMessage] = useState('');
  async function sendTagFeedback(tag, verdict) {
    if (!data.id || !tag?.tag) return;
    await api(`/api/media/${data.id}/tag-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag: tag.tag, category: tag.category || '', verdict }),
    });
    setFeedbackMessage(`${tag.tag}: ${t.tagFeedbackSaved}`);
  }
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
              <div className="row"><span>{t.originalName}</span><strong>{data.display_original_name || data.original_name || data.filename}</strong></div>
              <div className="row"><span>{t.indexedName}</span><strong>{data.filename}</strong></div>
              <div className="row"><span>{t.sourceOriginalPath}</span><strong>{data.source_original_path || '-'}</strong></div>
              <div className="row"><span>{t.filePath}</span><strong>{data.relative_path || data.filename}</strong></div>
              <div className="row"><span>{t.thumbnail}</span><strong>{data.resolution || data.quality || '-'}</strong></div>
              <div className="row"><span>{t.media}</span><strong>{data.media_type}</strong></div>
            </div>
            <h3>{t.tags}</h3>
            <div className="tagCloud tagFeedbackCloud">
              {tags.map(tag => (
                <span key={`${tag.tag}-${tag.source || ''}`} className={tag.state === 'rejected' ? 'rejectedTag' : ''}>
                  <b>{tag.tag}</b>{tag.confidence ? ` ${Math.round(Number(tag.confidence) * 100)}%` : ''}
                  <button title={t.tagCorrect} onClick={() => sendTagFeedback(tag, 'approve')}><CheckCircle2 size={13} /></button>
                  <button title={t.tagWrong} onClick={() => sendTagFeedback(tag, 'reject')}><XCircle size={13} /></button>
                </span>
              ))}
            </div>
            {feedbackMessage && <div className="hintBox smallHint"><span>{feedbackMessage}</span></div>}
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
            <h3>{t.transcript}</h3>
            {data.transcript?.text ? <pre className="transcriptBlock">{data.transcript.text}</pre> : <div className="empty smallEmpty">{t.noTranscript}</div>}
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
  const [selected, setSelected] = useState(null);
  const [media, setMedia] = useState({ items: [], total: 0 });
  async function openAuthor(author) {
    setSelected(author);
    setMedia({ items: [], total: 0 });
    const data = await api(`/api/authors/${encodeURIComponent(author.name)}/media?limit=120`);
    setMedia(data);
  }
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
          {filtered.map(author => <AuthorCard author={author} key={author.name} openAuthor={openAuthor} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />)}
        </section>
      ) : (
        <AuthorTable authors={filtered} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />
      )}
      {selected && <CollectionViewer title={selected.name} subtitle={`${selected.files} ${t.media}`} items={media.items || []} close={() => setSelected(null)} t={t} />}
    </>
  );
}

function AuthorCard({ author, openAuthor, renameAuthor, excludeAuthor, t }) {
  const [target, setTarget] = useState(author.name);
  useEffect(() => setTarget(author.name), [author.name]);
  return (
    <article className="authorCard clickableCard" onClick={() => openAuthor(author)}>
      <div className="authorThumb"><span>{author.name.slice(0, 2)}</span><img src={`${author.thumbnail_url}?v=${encodeURIComponent(author.files)}`} alt={author.name} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} /></div>
      <div className="authorMeta">
        <strong>{author.name}</strong>
        <div className="faceStats"><span>{author.files} {t.media}</span><span>{author.photos} {t.photos}</span><span>{author.videos} {t.videos}</span><span>{author.face_groups || 0} FaceGroups</span></div>
        <form onClick={event => event.stopPropagation()} onSubmit={event => { event.preventDefault(); renameAuthor(author.name, target); }}>
          <input value={target} onChange={event => setTarget(event.target.value)} placeholder={t.renameTo} />
          <button type="submit" title={t.renameTo}><Save size={15} /></button>
        </form>
        <button className="dangerButton" onClick={event => { event.stopPropagation(); excludeAuthor(author.name); }}><Archive size={15} />{t.excludeAuthor}</button>
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
  const [selected, setSelected] = useState(null);
  const [media, setMedia] = useState({ items: [], total: 0 });
  async function openFace(face) {
    setSelected(face);
    setMedia({ items: [], total: 0 });
    const data = await api(`/api/face-groups/${encodeURIComponent(face.face_group)}/media?limit=160`);
    setMedia(data);
  }
  return (
    <>
      <section className="panel">
        <div className="panelHead"><h2>{t.faceMergeSuggestions}</h2><span>{suggestions.length}</span></div>
        <div className="hintBox"><span>{t.faceMergeHelp}</span></div>
        {!suggestions.length ? <Empty label={t.noRows} /> : <div className="mergeGrid">{suggestions.slice(0, 40).map(item => <MergeCard item={item} key={`${item.left_group}-${item.right_group}`} mergeFace={mergeFace} t={t} />)}</div>}
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.faces}</h2><button className="panelButton" onClick={() => mergeNamedFaces('')}><Users size={16} />{t.mergeSameName}</button><span>{faces.length}</span></div>
        {!faces.length ? <Empty label={t.noRows} /> : <div className="faceGrid">{faces.map(face => <FaceCard face={face} key={face.face_group} openFace={openFace} nameFace={nameFace} t={t} />)}</div>}
      </section>
      {selected && <CollectionViewer title={selected.actor_name || selected.face_group} subtitle={selected.face_group} items={media.items || []} close={() => setSelected(null)} t={t} />}
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

function FaceCard({ face, openFace, nameFace, t }) {
  const [actor, setActor] = useState(face.actor_name || '');
  useEffect(() => setActor(face.actor_name || ''), [face.actor_name]);
  return (
    <article className="faceCard clickableCard" onClick={() => openFace(face)}>
      <div className="thumb"><img src={`${face.thumbnail_url}?v=${encodeURIComponent(face.representative_frame || '')}`} alt={face.face_group} loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} /></div>
      <div className="faceMeta">
        <strong>{face.face_group}</strong>
        <span>{face.actor_name ? `${t.namedAs}: ${face.actor_name}` : t.unnamed}</span>
        <div className="faceStats"><span>{face.media || face.group_media_count || 0} {t.media}</span><span>{face.faces || face.group_face_count || 0} {t.facesCount}</span></div>
        <form onClick={event => event.stopPropagation()} onSubmit={event => { event.preventDefault(); nameFace(face.face_group, actor); }}>
          <input value={actor} onChange={event => setActor(event.target.value)} placeholder={t.nameActor} />
          <button type="submit" title={t.saveName}><Save size={15} /></button>
        </form>
      </div>
    </article>
  );
}

function CollectionViewer({ title, subtitle, items, close, t }) {
  return (
    <div className="viewerBackdrop" role="dialog" aria-modal="true">
      <div className="viewerPanel collectionPanel">
        <div className="viewerHead"><div><h2>{title}</h2><p>{subtitle}</p></div><button className="iconButton" onClick={close}><XCircle size={18} /></button></div>
        <div className="collectionBody">
          <MediaGrid items={items} t={t} />
        </div>
      </div>
    </div>
  );
}

function LogsPanel({ jobs, applied, openJob, setActive, t }) {
  return <section className="panel"><div className="panelHead"><h2>{t.recentLogs}</h2><span>{applied.rows} {t.moveLogRows}</span></div><div className="jobs">{jobs.map(job => <button className="job" key={job.id} onClick={() => { openJob(job.id); setActive('jobs'); }}><div><strong>#{job.id} {job.command}</strong><p>{job.stdout || job.stderr || job.message || job.created_at}</p></div><JobBadge status={job.status} /></button>)}</div></section>;
}

function ModelsPanel({ catalog, pullModel, deleteModel, start, busy, t }) {
  const models = catalog?.models || [];
  const statusLabel = {
    ready: t.modelReady,
    missing: t.modelMissing,
    needs_url: t.modelNeedsUrl,
  };
  const recommended = models.filter(model => model.recommended && model.status !== 'ready').length;
  return (
    <section className="panel modelPanel">
      <div className="panelHead">
        <div>
          <h2>{t.modelManager}</h2>
          <p>{t.modelHint}</p>
        </div>
        <div className="panelActions">
          <span>{t.modelRoot}: {catalog?.root || '/models'}</span>
          <button className="panelButton" disabled={busy || recommended === 0} onClick={() => start('model-pull-recommended')}><Download size={16} />{t.downloadRecommended}</button>
        </div>
      </div>
      <div className="modelGrid">
        {models.map(model => (
          <article className={`modelCard ${model.status}`} key={model.id}>
            <div className="modelCardTop">
              <HardDrive size={20} />
              <div>
                <strong>{model.name}</strong>
                <span>{model.category} · {model.kind === 'file' ? t.modelFile : t.modelRuntimeCache}</span>
              </div>
              <b>{statusLabel[model.status] || model.status}</b>
            </div>
            <p>{model.description}</p>
            <div className="modelMeta">
              <div><span>{t.modelSize}</span><strong>{prettyBytes(model.bytes)}</strong></div>
              <div><span>{t.modelPath}</span><strong title={model.path}>{model.path}</strong></div>
              {model.url_env && <div><span>URL env</span><strong>{model.url_env}{model.url_configured ? '' : ' unset'}</strong></div>}
            </div>
            <div className="modelActions">
              <button className="panelButton" disabled={busy || model.status === 'needs_url'} onClick={() => pullModel(model.id)}><Download size={16} />{t.downloadModel}</button>
              <button className="panelButton dangerButton" disabled={!model.present || busy} onClick={() => deleteModel(model.id)}><Trash2 size={16} />{t.deleteModel}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function SettingsPanel({ settings, setSettings, saveSettings, browse, directories, browsePath, monitor, checkMonitorNow, t }) {
  const cfg = settings || {
    media_root: '/media',
    output_root: '/media',
    source_dirs: '',
    language: 'zh-CN',
    compute_device: 'auto',
    ffmpeg_hwaccel: 'auto',
    openvino_device: 'GPU',
    openclip_model: 'ViT-L-14',
    openclip_pretrained: 'laion2b_s32b_b82k',
    openclip_strong_model: 'ViT-H-14',
    openclip_strong_pretrained: 'laion2b_s32b_b79k',
    openclip_strong_threshold: 0.62,
    openclip_strong_low_conf_only: true,
    face_providers: 'OpenVINOExecutionProvider,CPUExecutionProvider',
    whisper_device: 'cpu',
    asr_engine: 'auto',
    sensevoice_gguf_bin: 'llama-sensevoice',
    sensevoice_gguf_model: '/models/sensevoice/SenseVoiceSmall.gguf',
    sensevoice_gguf_command: '',
    frame_workers: 1,
    frames_per_video: 3,
    frame_checkpoint_every: 100,
    transcribe_max_seconds: 0,
    monitor_enabled: false,
    monitor_dirs: '',
    monitor_interval_minutes: 10,
    browse_roots: ['/media'],
  };
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
          <div className="formSectionTitle">{t.hardware}</div>
          <label>{t.computeDevice}<select value={cfg.compute_device || 'auto'} onChange={event => update('compute_device', event.target.value)}><option value="auto">{t.auto}</option><option value="gpu">{t.gpuPreferred}</option><option value="cpu">{t.cpuOnly}</option></select><small>{t.gpuHint}</small></label>
          <label>{t.ffmpegHwaccel}<select value={cfg.ffmpeg_hwaccel || 'auto'} onChange={event => update('ffmpeg_hwaccel', event.target.value)}><option value="auto">{t.auto}</option><option value="vaapi">VAAPI</option><option value="qsv">Intel QSV</option><option value="none">{t.ffmpegNone}</option></select></label>
          <label>Frame workers<input type="number" min="1" max="16" value={cfg.frame_workers || 1} onChange={event => update('frame_workers', event.target.value)} /><small>NAS 建议 3-4；太高会打满磁盘 IO。</small></label>
          <label>Frames per video<input type="number" min="1" max="12" value={cfg.frames_per_video || 3} onChange={event => update('frames_per_video', event.target.value)} /></label>
          <label>Checkpoint every<input type="number" min="10" max="1000" value={cfg.frame_checkpoint_every || 100} onChange={event => update('frame_checkpoint_every', event.target.value)} /><small>抽帧索引和任务进度的落盘频率。</small></label>
          <label>{t.openvinoDevice}<select value={cfg.openvino_device || 'GPU'} onChange={event => update('openvino_device', event.target.value)}><option value="GPU">{t.gpu}</option><option value="CPU">{t.cpu}</option><option value="AUTO">{t.openvinoAuto}</option></select></label>
          <label>{t.openclipModel}<input value={cfg.openclip_model || 'ViT-L-14'} onChange={event => update('openclip_model', event.target.value)} placeholder="ViT-L-14" /><small>{t.openclipHint}</small></label>
          <label>{t.openclipPretrained}<input value={cfg.openclip_pretrained || 'laion2b_s32b_b82k'} onChange={event => update('openclip_pretrained', event.target.value)} placeholder="laion2b_s32b_b82k" /></label>
          <label>{t.openclipStrongModel}<input value={cfg.openclip_strong_model || 'ViT-H-14'} onChange={event => update('openclip_strong_model', event.target.value)} placeholder="ViT-H-14" /></label>
          <label>{t.openclipStrongPretrained}<input value={cfg.openclip_strong_pretrained || 'laion2b_s32b_b79k'} onChange={event => update('openclip_strong_pretrained', event.target.value)} placeholder="laion2b_s32b_b79k" /></label>
          <label>{t.openclipStrongThreshold}<input type="number" min="0.01" max="0.99" step="0.01" value={cfg.openclip_strong_threshold ?? 0.62} onChange={event => update('openclip_strong_threshold', event.target.value)} /></label>
          <label className="checkLine"><input type="checkbox" checked={cfg.openclip_strong_low_conf_only !== false} onChange={event => update('openclip_strong_low_conf_only', event.target.checked)} />{t.openclipStrongLowOnly}</label>
          <label>{t.faceProviders}<select value={cfg.face_providers || 'OpenVINOExecutionProvider,CPUExecutionProvider'} onChange={event => update('face_providers', event.target.value)}><option value="OpenVINOExecutionProvider,CPUExecutionProvider">OpenVINO + CPU fallback</option><option value="CPUExecutionProvider">CPUExecutionProvider</option></select></label>
          <label>{t.asrEngine}<select value={cfg.asr_engine || 'auto'} onChange={event => update('asr_engine', event.target.value)}><option value="auto">{t.asrAuto}</option><option value="sensevoice-gguf">{t.asrSenseVoice}</option><option value="faster-whisper">{t.asrWhisper}</option></select></label>
          <label>{t.senseVoiceModel}<input value={cfg.sensevoice_gguf_model || '/models/sensevoice/SenseVoiceSmall.gguf'} onChange={event => update('sensevoice_gguf_model', event.target.value)} /></label>
          <label>{t.senseVoiceBin}<input value={cfg.sensevoice_gguf_bin || 'llama-sensevoice'} onChange={event => update('sensevoice_gguf_bin', event.target.value)} /></label>
          <label>{t.senseVoiceCommand}<input value={cfg.sensevoice_gguf_command || ''} onChange={event => update('sensevoice_gguf_command', event.target.value)} placeholder="{bin} -m {model} -f {audio} --language auto" /><small>{t.senseVoiceCommandHint}</small></label>
          <label>{t.whisperDevice}<select value={cfg.whisper_device || 'cpu'} onChange={event => update('whisper_device', event.target.value)}><option value="cpu">{t.cpu}</option><option value="cuda">CUDA</option></select></label>
          <label>{t.transcribeMaxSeconds}<input type="number" min="0" max="86400" value={cfg.transcribe_max_seconds ?? 0} onChange={event => update('transcribe_max_seconds', event.target.value)} /><small>{t.transcribeFullHint}</small></label>
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
      <div className="panel">
        <div className="panelHead"><h2>{t.privacyTitle}</h2><span>{t.localOnly}</span></div>
        <div className="hintBox"><span>{t.privacyCopy}</span></div>
        <div className="list">
          <div className="row"><span>APP_PASSWORD</span><strong>{t.password}</strong></div>
          <div className="row"><span>Risk queue</span><strong>_QUARANTINE / review</strong></div>
          <div className="row"><span>Audit log</span><strong>jobs + media_operations</strong></div>
        </div>
      </div>
    </section>
  );
}

createRoot(document.getElementById('root')).render(<App />);
