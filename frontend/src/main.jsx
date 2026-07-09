import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  Archive,
  Bell,
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
  Heart,
  HelpCircle,
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

const THUMBNAIL_REVISION = 'v8';
const DEFAULT_MEDIA_FILTERS = {
  q: '',
  media_type: 'all',
  tag: '',
  author: '',
  face_group: '',
  favorite: '',
  has_subtitles: '',
  min_duration: '',
  max_duration: '',
  resolution: '',
  semantic: '',
};

function compactSearchParams(values) {
  const search = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  return search;
}

const i18n = {
  en: {
    locale: 'en',
    app: 'Private Library',
    manager: 'TG Media Manager',
    lockAction: 'Privacy lock: hide details',
    version: 'Version',
    build: 'build',
    title: 'Library Console',
    dashboard: 'Dashboard',
    jobs: 'Jobs',
    quickFind: 'Quick Find',
    library: 'Library',
    virtualLibrary: 'Virtual Library',
    tagGraph: 'Tag Graph',
    randomFlow: 'Random Flow',
    models: 'Models',
    diagnostics: 'Diagnostics',
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
    totalCapacity: 'Total indexed',
    videoUnit: 'videos',
    photoUnit: 'photos',
    itemUnit: 'items',
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
    latestFirst: 'Newest first',
    moveLogRows: 'move log rows',
    jobLog: 'Job Log',
    selectJob: 'select a job',
    selectJobHint: 'Select a job to inspect stdout and stderr',
    normalJobs: 'Normal',
    runningJobs: 'Running',
    allJobs: 'All',
    warningJobs: 'Warnings',
    errorJobs: 'Errors',
    failedJobs: 'Errors',
    completedJobs: 'Completed',
    otherJobs: 'Other',
    jobHistoryHint: 'Failed records can include old restarts or manual stops. They are kept as audit history; use the filters to separate warnings from real errors.',
    jobInterruptedHint: 'Interrupted by service restart. Cached outputs were kept and the job can be rerun.',
    jobCancelledHint: 'Cancelled by user. Finished cache files were kept and the workflow can resume later.',
    jobStaleHint: 'No heartbeat for a while. The worker may be stalled or the browser is showing stale data.',
    workflowStep: 'Step',
    remainingSteps: 'remaining',
    workflowProgress: 'Workflow progress',
    currentStepProgress: 'Current step',
    failedShort: 'failed',
    loadingMore: 'Loading more...',
    loadingDetail: 'Loading details...',
    loadFailed: 'Load failed',
    scrollForMore: 'Scroll to load more',
    noMoreMedia: 'No more media',
    activeFilters: 'Active filters',
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
    transcriptEngine: 'Subtitle engine',
    audioTagMode: 'Audio tag mode',
    audioTagOff: 'No audio tags',
    audioTagSenseVoiceSample: 'SenseVoice sampled tags',
    audioTagSenseVoiceFull: 'SenseVoice full-audio tags',
    audioTagSampleSeconds: 'Audio tag sample seconds',
    asrAuto: 'Auto: SenseVoice first, then Whisper',
    transcriptAuto: 'Auto: Nano/ONNX, then SenseVoice, then Whisper',
    asrFunAsrNano: 'Fun-ASR-Nano ONNX',
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
    settingHelp: {
      computeDevice: 'Global preference for inference jobs. Auto will use GPU where supported and fall back to CPU.',
      ffmpegHwaccel: 'Hardware video decoding for frame extraction. VAAPI is Intel iGPU on most Linux NAS devices; QSV is Intel Quick Sync.',
      frameWorkers: 'How many videos are decoded in parallel. More workers can be faster, but heavy disks may become the bottleneck.',
      framesPerVideo: 'How many still frames are sampled from each video for vision and face analysis.',
      checkpointEvery: 'How often progress and frame indexes are saved. Smaller values resume more precisely; larger values write less often.',
      openvinoDevice: 'Device used by OpenVINO models. GPU uses Intel iGPU/NPU when available; AUTO lets OpenVINO decide.',
      openclipModel: 'OpenCLIP architecture for scene/tag recognition. ViT-L is balanced; ViT-H is slower but stronger.',
      openclipPretrained: 'The pretrained weight set paired with the OpenCLIP architecture.',
      openclipStrongThreshold: 'Confidence cutoff for second-pass vision tagging. Higher is stricter and sends more media to review.',
      faceProviders: 'Runtime used by face models. OpenVINO can use Intel acceleration, then CPU is used as fallback.',
      asrEngine: 'Speech-to-text backend. Auto prefers configured local models and falls back when needed.',
      transcriptEngine: 'Engine used for subtitles and searchable transcript text. Nano/ONNX is intended for fast CPU batch transcription.',
      audioTagMode: 'Optional second pass for voice mood, speech presence, music, laughter, and acoustic tags. Sample mode keeps it cheap.',
      audioTagSampleSeconds: 'How many seconds SenseVoice samples for audio tags when sample mode is selected.',
      whisperDevice: 'Device for faster-whisper. Keep CPU on this NAS unless CUDA hardware is available.',
      transcribeMaxSeconds: '0 means transcribe full video audio. Set a limit only for quick sampling.',
    },
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
    modelNeedsUrl: 'Needs download URL',
    modelBusyHint: 'A job is running. Model downloads are paused until the current job finishes.',
    modelRuntimeCache: 'Runtime cache',
    modelFile: 'File model',
    modelHint: 'Models are not baked into the Docker image. They are downloaded into /models and survive container updates.',
    modelSourceUrl: 'Source URL',
    modelUrlSourceDefault: 'Using built-in verified default URL. You can override it here.',
    modelUrlSourceSettings: 'Using custom URL saved in Web settings.',
    modelUrlSourceEnv: 'Using URL from environment variable.',
    modelUrlSourceMissing: 'No default URL is available. Paste a direct model file URL or upload your own model pack.',
    modelSha256: 'SHA256',
    modelOfficialRef: 'Official reference',
    modelManifestUrl: 'Manifest URL',
    saveModelSource: 'Save source',
    modelSourceSaved: 'Model source saved',
    modelManifestHint: 'Future model packs can be installed from a JSON manifest. For now it is stored as the preferred pack source.',
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
    transcriptSegments: 'Timed transcript',
    textTranscriptOnly: 'Text transcript only; no reliable subtitle timestamps yet.',
    subtitles: 'Subtitles',
    originalSubtitles: 'Original subtitles',
    bilingualSubtitles: 'Bilingual subtitles',
    noTranscript: 'No transcript yet',
    mediaSearch: 'Search media, tags, authors',
    quickFindTitle: 'Quick Find',
    quickFindHint: 'Search-first view for author, tag, filename, subtitle text, and visual labels. Use it when you want to find media, not maintain the library.',
    searchNow: 'Search now',
    advancedFilters: 'Advanced filters',
    faceGroupFilter: 'Face group',
    favoriteAny: 'Favorite: any',
    favoriteOnly: 'Favorites only',
    favoriteExclude: 'Exclude favorites',
    subtitleAny: 'Subtitles: any',
    subtitleOnly: 'Has subtitles',
    subtitleMissing: 'No subtitles',
    minDurationSeconds: 'Min seconds',
    maxDurationSeconds: 'Max seconds',
    resolutionFilter: 'Resolution',
    semanticMode: 'Semantic ranking',
    semanticScore: 'Semantic',
    semanticFallbackHint: 'Uses local BGE/OpenCLIP vectors when ready; otherwise falls back to filename, tags, subtitles, and hash vectors.',
    understoodQuery: 'Understood',
    recentSearches: 'Recent searches',
    savedSearch: 'Saved search',
    savedSearchName: 'Saved search name',
    saveSearch: 'Save search',
    capabilityCenter: 'Capability Center',
    coreCapabilities: 'Core / system capabilities',
    downloadableCapabilities: 'Downloadable model capabilities',
    capabilityReady: 'Ready',
    capabilityPartial: 'Partial',
    capabilityMissing: 'Missing',
    builtIn: 'Built-in',
    deleteable: 'Deleteable',
    notDeleteable: 'Not deleteable',
    purpose: 'Purpose',
    source: 'Source',
    localRuntimeStatus: 'Local runtime status',
    databasePath: 'Database path',
    modelDownloads: 'Model downloads',
    remoteModels: 'Remote models',
    missingModels: 'Missing models',
    recentFailures: 'Recent failures',
    noFailures: 'No recent failed jobs',
    diagnosticsTitle: 'Search Capability',
    diagnosticsHint: 'Index coverage, metadata completeness, thumbnail cache, transcripts, and next actions for local search.',
    thumbnailHealth: 'Thumbnail health',
    thumbnailHealthHint: 'Sampled cached previews. Unhealthy previews are likely corrupt hardware-decoded frames and can be repaired in batch.',
    coverage: 'Coverage',
    nextActions: 'Next actions',
    runAction: 'Run action',
    metadataBackfill: 'Metadata backfill',
    metadataBackfillHint: 'Fill missing duration, dimensions, and resolution without moving files.',
    allMedia: 'All media',
    photosOnly: 'Photos',
    videosOnly: 'Videos',
    openMedia: 'Open',
    mediaDetail: 'Media detail',
    mediaZoom: 'Media zoom',
    smallerCards: 'Smaller',
    largerCards: 'Larger',
    close: 'Close',
    originalName: 'Original name',
    sourceOriginalPath: 'Original source path',
    indexedName: 'Library filename',
    filePath: 'File path',
    tags: 'Tags',
    tagCorrect: 'Correct',
    tagWrong: 'Wrong',
    tagFeedbackSaved: 'Feedback saved',
    favorite: 'Favorite',
    unfavorite: 'Unfavorite',
    favoriteSaved: 'Favorite updated',
    deleteMedia: 'Delete media',
    deleteMediaConfirm: 'Move this media to _REVIEW/Deleted? It will not be physically destroyed.',
    mediaDeleted: 'Moved to Deleted review folder',
    rebuildThumbnail: 'Rebuild thumbnail',
    thumbnailRebuilt: 'Thumbnail rebuilt',
    rebuildVideoOverview: 'Rebuild video overview',
    videoOverviewRebuilt: 'Video overview rebuilt',
    manualTag: 'Manual tag',
    addTag: 'Add tag',
    tagCategory: 'Category',
    saveAuthor: 'Save author',
    manualEditSaved: 'Saved',
    trainVisionCalibrator: 'Train calibrator',
    videoOverview: 'Video overview',
    videoOverviewMissing: 'Video overview is not available yet',
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
    runningJobGuard: 'Another job is running. Stop it or wait for it to finish before starting a new job.',
    cancelRequested: 'Stop request sent. Waiting for the current step to exit safely.',
    cacheDeleted: 'Cache deleted',
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
      'metadata-backfill': 'Metadata Backfill',
      'repair-thumbnails': 'Repair Thumbnails',
      'index-similarity': 'Similarity Index',
      'index-semantic-text': 'Text Semantic Index',
      'index-semantic-vision': 'Vision Semantic Index',
      'index-semantic-all': 'Semantic Index',
      'diagnose-search': 'Diagnose Search',
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
      'model-pull-funasr-nano-onnx': 'Download Fun-ASR-Nano ONNX',
      'model-pull-bge-small-text': 'Download BGE Text',
      'model-pull-sensevoice-small-gguf': 'Download SenseVoice GGUF',
      'model-pull-sensevoice-fsmn-vad-gguf': 'Download SenseVoice VAD',
      'model-pull-sensevoice-llamacpp-runtime': 'Download SenseVoice Runtime',
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
      'metadata-backfill': 'Fill missing duration, dimensions, and resolution using local ffprobe/Pillow.',
      'repair-thumbnails': 'Check and rebuild missing or corrupted media thumbnails. Photos use Pillow; videos use software FFmpeg fallback.',
      'index-similarity': 'Build exact duplicate, image perceptual hash, and video keyframe similarity groups.',
      'index-semantic-text': 'Build BGE/hash vectors for filenames, tags, authors, subtitles, and transcript text.',
      'index-semantic-vision': 'Build OpenCLIP/hash vectors from cached image and video keyframes.',
      'index-semantic-all': 'Refresh both text and visual semantic search indexes.',
      'diagnose-search': 'Print search capability coverage and missing model/index diagnostics.',
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
      'model-pull-funasr-nano-onnx': 'Download/cache the optional Fun-ASR-Nano ONNX subtitle model pack.',
      'model-pull-bge-small-text': 'Download/cache the optional BGE text embedding model for semantic search.',
      'model-pull-sensevoice-small-gguf': 'Download the SenseVoice GGUF file from the Web-configured URL.',
      'model-pull-sensevoice-fsmn-vad-gguf': 'Download the FSMN VAD GGUF file required by SenseVoice runtime.',
      'model-pull-sensevoice-llamacpp-runtime': 'Download and unpack the FunASR llama.cpp runtime for SenseVoice.',
      'model-pull-custom-detector-onnx': 'Download the optional custom detector from the Web-configured URL.',
    },
  },
  'zh-CN': {
    locale: 'zh-CN',
    app: '私享影库',
    manager: 'TG Media Manager',
    lockAction: '隐私锁：隐藏详情',
    version: '版本',
    build: '构建',
    title: '影库控制台',
    dashboard: '概览',
    jobs: '任务',
    quickFind: '快找',
    library: '媒体库',
    virtualLibrary: '虚拟媒体库',
    tagGraph: '标签图谱',
    randomFlow: '随机瀑布流',
    models: '模型',
    diagnostics: '搜索能力',
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
    totalCapacity: '索引总量',
    videoUnit: '部',
    photoUnit: '张',
    itemUnit: '项',
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
    latestFirst: '最新在前',
    moveLogRows: '移动日志行',
    jobLog: '任务日志',
    selectJob: '选择任务',
    selectJobHint: '选择一个任务查看 stdout 和 stderr',
    normalJobs: '正常',
    runningJobs: '进行中',
    allJobs: '全部',
    warningJobs: '警告',
    errorJobs: '错误',
    failedJobs: '错误',
    completedJobs: '已完成',
    otherJobs: '其他',
    jobHistoryHint: '失败记录里可能包含旧版本重启中断或手动停止。它们会保留作为审计历史，可以用筛选区分警告和真实错误。',
    jobInterruptedHint: '服务重启导致中断。已完成的缓存会保留，可以重新运行继续补齐。',
    jobCancelledHint: '用户手动停止。已完成的缓存会保留，后续可继续跑。',
    jobStaleHint: '一段时间没有心跳。可能是任务卡住，也可能是页面状态未刷新。',
    workflowStep: '第',
    remainingSteps: '剩余',
    workflowProgress: '流程进度',
    currentStepProgress: '当前步骤',
    failedShort: '失败',
    loadingMore: '继续加载中...',
    loadingDetail: '正在加载详情...',
    loadFailed: '加载失败',
    scrollForMore: '下滑继续加载',
    noMoreMedia: '已经到底了',
    activeFilters: '当前筛选',
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
    transcriptEngine: '字幕转写引擎',
    audioTagMode: '音频标签模式',
    audioTagOff: '不生成音频标签',
    audioTagSenseVoiceSample: 'SenseVoice 抽样标签',
    audioTagSenseVoiceFull: 'SenseVoice 全音频标签',
    audioTagSampleSeconds: '音频标签抽样秒数',
    asrAuto: '自动：优先 SenseVoice，再回退 Whisper',
    transcriptAuto: '自动：Nano/ONNX、SenseVoice、Whisper 依次回退',
    asrFunAsrNano: 'Fun-ASR-Nano ONNX',
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
    settingHelp: {
      computeDevice: '全局推理偏好。自动模式会优先使用可用 GPU，不支持时回退 CPU。',
      ffmpegHwaccel: '视频抽帧时的硬件解码。VAAPI 通常对应 Linux NAS 的 Intel 核显；QSV 是 Intel Quick Sync。',
      frameWorkers: '同时解码多少个视频。数值越高不一定越快，磁盘 IO 可能先被打满。',
      framesPerVideo: '每个视频抽取多少张静帧用于视觉识别和人脸识别。',
      checkpointEvery: '任务进度和抽帧索引的落盘频率。越小越利于断点续跑，越大写盘更少。',
      openvinoDevice: 'OpenVINO 模型使用的设备。GPU 会走 Intel 核显/NPU；AUTO 由 OpenVINO 自行选择。',
      openclipModel: 'OpenCLIP 视觉识别模型结构。ViT-L 比较均衡；ViT-H 更强但更慢。',
      openclipPretrained: '与 OpenCLIP 模型结构配套的预训练权重。',
      openclipStrongThreshold: '强扫二次识别的置信度阈值。越高越严格，也会让更多媒体进入待确认。',
      faceProviders: '人脸模型运行后端。OpenVINO 可用 Intel 加速，CPU 作为兜底。',
      asrEngine: '语音转文字引擎。自动会优先使用已配置的本地模型。',
      transcriptEngine: '用于字幕和可搜索转写文本的引擎。Nano/ONNX 适合 NAS CPU 批量转写。',
      audioTagMode: '可选第二遍音频标签，用于声线情绪、有人声、音乐、笑声、环境声等。抽样模式成本低。',
      audioTagSampleSeconds: '抽样标签模式下，每个视频让 SenseVoice 采样多少秒。',
      whisperDevice: 'faster-whisper 使用的设备。NAS 没有 CUDA 时保持 CPU。',
      transcribeMaxSeconds: '0 表示完整识别视频音频；只想快速抽样时再设置秒数上限。',
    },
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
    modelNeedsUrl: '需要下载 URL',
    modelBusyHint: '当前有任务正在运行，模型下载会等任务结束后再操作。',
    modelRuntimeCache: '运行时缓存',
    modelFile: '文件模型',
    modelHint: '模型不会打进 Docker 镜像，会下载到 /models；容器升级后缓存仍然保留。',
    modelSourceUrl: '模型下载 URL',
    modelUrlSourceDefault: '正在使用内置已验证默认链接；你也可以在这里覆盖。',
    modelUrlSourceSettings: '正在使用 Web 设置中保存的自定义链接。',
    modelUrlSourceEnv: '正在使用环境变量里的链接。',
    modelUrlSourceMissing: '没有可用默认链接，请填入直连模型文件 URL，或使用你自己的模型包。',
    modelSha256: 'SHA256 校验',
    modelOfficialRef: '官方参考',
    modelManifestUrl: '模型包 Manifest URL',
    saveModelSource: '保存来源',
    modelSourceSaved: '模型来源已保存',
    modelManifestHint: '后续模型包会从 JSON Manifest 一键安装；当前先作为默认模型包来源保存。',
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
    transcriptSegments: '分段转写',
    textTranscriptOnly: '当前只有文本转写，还没有可靠的字幕时间轴。',
    subtitles: '字幕',
    originalSubtitles: '原文字幕',
    bilingualSubtitles: '双语字幕',
    noTranscript: '还没有转写内容',
    mediaSearch: '搜索媒体、标签、作者',
    quickFindTitle: '快找',
    quickFindHint: '面向检索的入口：按作者、标签、文件名、字幕文字和视觉标签找媒体。想找内容时从这里开始。',
    searchNow: '立即搜索',
    advancedFilters: '高级筛选',
    faceGroupFilter: '人脸组',
    favoriteAny: '收藏：不限',
    favoriteOnly: '只看收藏',
    favoriteExclude: '排除收藏',
    subtitleAny: '字幕：不限',
    subtitleOnly: '有字幕',
    subtitleMissing: '无字幕',
    minDurationSeconds: '最小时长秒',
    maxDurationSeconds: '最大时长秒',
    resolutionFilter: '分辨率',
    semanticMode: '语义排序',
    semanticScore: '语义',
    semanticFallbackHint: '本地 BGE/OpenCLIP 就绪时使用向量排序；模型缺失时自动用文件名、标签、字幕和 hash 向量兜底。',
    understoodQuery: '已理解为',
    recentSearches: '最近搜索',
    savedSearch: '保存的搜索',
    savedSearchName: '搜索条件名称',
    saveSearch: '保存搜索',
    capabilityCenter: '能力中心',
    coreCapabilities: '核心 / 系统能力',
    downloadableCapabilities: '可下载模型能力',
    capabilityReady: '已就绪',
    capabilityPartial: '部分就绪',
    capabilityMissing: '缺失',
    builtIn: '内置',
    deleteable: '可删除',
    notDeleteable: '不可删除',
    purpose: '用途',
    source: '来源',
    localRuntimeStatus: '本地运行状态',
    databasePath: '数据库路径',
    modelDownloads: '模型下载',
    remoteModels: '远程模型',
    missingModels: '缺失模型',
    recentFailures: '最近失败任务',
    noFailures: '最近没有失败任务',
    diagnosticsTitle: '搜索能力诊断',
    diagnosticsHint: '检查索引覆盖率、元数据完整度、缩略图缓存、字幕转写和下一步建议。',
    thumbnailHealth: '缩略图健康度',
    thumbnailHealthHint: '抽样检查缓存预览图。坏图通常是硬解抽帧色彩异常或旧缓存，可批量修复。',
    coverage: '覆盖率',
    nextActions: '下一步建议',
    runAction: '执行',
    metadataBackfill: '元数据回填',
    metadataBackfillHint: '不移动文件，只补齐时长、宽高、分辨率等信息。',
    allMedia: '全部媒体',
    photosOnly: '照片',
    videosOnly: '视频',
    openMedia: '打开',
    mediaDetail: '媒体详情',
    mediaZoom: '媒体缩放',
    smallerCards: '更小',
    largerCards: '更大',
    close: '关闭',
    originalName: '原始文件名',
    sourceOriginalPath: '最初来源路径',
    indexedName: '库内文件名',
    filePath: '文件路径',
    tags: '标签',
    tagCorrect: '正确',
    tagWrong: '错误',
    tagFeedbackSaved: '反馈已保存',
    favorite: '收藏',
    unfavorite: '取消收藏',
    favoriteSaved: '收藏已更新',
    deleteMedia: '删除媒体',
    deleteMediaConfirm: '把这个媒体移动到 _REVIEW/Deleted？不会物理销毁文件。',
    mediaDeleted: '已移动到 Deleted 待审目录',
    rebuildThumbnail: '重建缩略图',
    thumbnailRebuilt: '缩略图已重建',
    rebuildVideoOverview: '重建视频概览',
    videoOverviewRebuilt: '视频概览已重建',
    manualTag: '手动标签',
    addTag: '添加标签',
    tagCategory: '分类',
    saveAuthor: '保存作者',
    manualEditSaved: '已保存',
    trainVisionCalibrator: '训练校准器',
    videoOverview: '视频概览',
    videoOverviewMissing: '暂时没有可用的视频概览',
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
    runningJobGuard: '已有任务正在运行。请先停止或等待完成后再启动新任务。',
    cancelRequested: '已发送停止请求，正在等待当前步骤安全退出。',
    cacheDeleted: '缓存已删除',
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
      'metadata-backfill': '元数据回填',
      'repair-thumbnails': '修复缩略图',
      'index-similarity': '相似索引',
      'index-semantic-text': '文本语义索引',
      'index-semantic-vision': '视觉语义索引',
      'index-semantic-all': '语义索引',
      'diagnose-search': '诊断搜索能力',
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
      'model-pull-funasr-nano-onnx': '下载 Fun-ASR-Nano ONNX',
      'model-pull-bge-small-text': '下载 BGE 文本向量',
      'model-pull-sensevoice-small-gguf': '下载 SenseVoice GGUF',
      'model-pull-sensevoice-fsmn-vad-gguf': '下载 SenseVoice VAD',
      'model-pull-sensevoice-llamacpp-runtime': '下载 SenseVoice 运行时',
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
      'metadata-backfill': '用本地 ffprobe/Pillow 补齐缺失的时长、尺寸和分辨率。',
      'repair-thumbnails': '检查并重建缺失/损坏的媒体缩略图。图片用 Pillow，视频用软件 FFmpeg 兜底。',
      'index-similarity': '生成精确重复、图片感知 hash、视频关键帧相似组。',
      'index-semantic-text': '为文件名、标签、作者、字幕和转写文字生成 BGE/hash 向量。',
      'index-semantic-vision': '从缓存图片和视频关键帧生成 OpenCLIP/hash 视觉向量。',
      'index-semantic-all': '刷新文本和视觉两类语义搜索索引。',
      'diagnose-search': '输出搜索覆盖率、缺失模型和索引诊断。',
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
      'model-pull-funasr-nano-onnx': '下载/缓存可选 Fun-ASR-Nano ONNX 字幕模型包。',
      'model-pull-bge-small-text': '下载/缓存可选 BGE 文本向量模型，用于语义搜索。',
      'model-pull-sensevoice-small-gguf': '从 Web 配置的 URL 下载 SenseVoice GGUF 文件。',
      'model-pull-sensevoice-fsmn-vad-gguf': '下载 SenseVoice 运行时需要的 FSMN VAD GGUF 文件。',
      'model-pull-sensevoice-llamacpp-runtime': '下载并解压 SenseVoice 的 FunASR llama.cpp 运行时。',
      'model-pull-custom-detector-onnx': '从 Web 配置的 URL 下载可选自定义检测模型。',
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
  ['metadata-backfill', 'Metadata Backfill', Database, 'Fill duration, dimensions, and resolution'],
  ['repair-thumbnails', 'Repair Thumbnails', Camera, 'Repair missing or corrupted thumbnail cache'],
  ['index-similarity', 'Similarity Index', Archive, 'Build duplicate and similarity groups'],
  ['index-semantic-text', 'Semantic Text', Search, 'Build text, tag, and subtitle vectors for smart search'],
  ['index-semantic-vision', 'Semantic Vision', Camera, 'Import visual vectors for similar image/video search'],
  ['index-semantic-all', 'Semantic All', Search, 'Refresh all smart search vectors'],
  ['diagnose-search', 'Search Diagnose', HelpCircle, 'Inspect search capability coverage'],
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
  ['quickFind', 'quickFind', Search],
  ['library', 'library', Folder],
  ['authors', 'authors', Users],
  ['faces', 'faces', Users],
  ['tagGraph', 'tagGraph', Share2],
  ['models', 'models', HardDrive],
  ['diagnostics', 'diagnostics', HelpCircle],
  ['jobs', 'jobs', Activity],
  ['logs', 'logs', TerminalSquare],
  ['settings', 'settings', Settings],
];

const workflowSteps = {
  'workflow-new-downloads': ['scan', 'filename-analysis', 'keyword-classification', 'apply-move-plan', 'refresh-state', 'index-metadata'],
  'workflow-review-cleanup': ['normalize', 'keyword-classification', 'review-cleanup', 'refresh-state', 'index-metadata'],
  'workflow-face-balanced': ['extract-frames', 'face-scan', 'face-cluster', 'face-report', 'apply-face-groups'],
  'workflow-vision-plan': ['extract-frames', 'vision-scan', 'index-vision', 'apply-vision-labels'],
  'workflow-full-library': ['scan', 'filename-analysis', 'keyword-classification', 'apply-move-plan', 'normalize', 'review-cleanup', 'refresh-state', 'extract-frames', 'face-scan', 'face-cluster', 'face-report', 'apply-face-groups', 'vision-scan', 'index-vision', 'apply-vision-labels', 'dedupe', 'index-similarity', 'transcribe', 'index-metadata', 'metadata-backfill', 'index-semantic-all'],
  'workflow-transcribe-sample': ['transcribe', 'index-metadata'],
  'model-pull-recommended': ['model-download', 'model-download', 'model-download', 'model-download', 'model-download'],
};

function api(path, options) {
  return fetch(path, options).then(async response => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || response.statusText);
    return data;
  });
}

function Stat({ label, value, icon: Icon, tone = 'blue', sub = '', onClick }) {
  const Tag = onClick ? 'button' : 'div';
  return <Tag className={`stat ${tone} ${onClick ? 'clickable' : ''}`} onClick={onClick || undefined}><div className="statIcon"><Icon size={24} /></div><div><div className="statValue">{value ?? 0}</div><div className="statLabel">{label}</div>{sub && <div className="statSub">{sub}</div>}</div></Tag>;
}

function JobBadge({ status, kind, label }) {
  const tone = kind || (status === 'done' ? 'completed' : status === 'failed' ? 'error' : status);
  const Icon = tone === 'completed' ? CheckCircle2 : tone === 'error' ? XCircle : Activity;
  return <span className={`badge ${tone} ${status}`}><Icon size={13} />{label || status}</span>;
}

function formatDateTime(value) {
  if (!value) return '-';
  const raw = String(value).trim().replace('T', ' ').replace(/\.\d+$/, '');
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return raw;
  const [, year, month, day, hour, minute, second = '00'] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second)));
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(date).replace(/\//g, '-');
  } catch {
    return raw;
  }
}

function sortJobsNewest(jobs) {
  return [...(jobs || [])].sort((a, b) => Number(b.id || 0) - Number(a.id || 0));
}

function parseJobTime(value) {
  if (!value) return null;
  const raw = String(value).trim().replace('T', ' ').replace(/\.\d+$/, '');
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return null;
  const [, year, month, day, hour, minute, second = '00'] = match;
  return Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second));
}

function jobTextBlob(job) {
  return [job?.message, job?.stdout, job?.stderr].filter(Boolean).join('\n').toLowerCase();
}

function isInterruptedJob(job) {
  return job?.status === 'failed' && jobTextBlob(job).includes('interrupted by service restart');
}

function isCancelledJob(job) {
  return job?.status === 'cancelled' || jobTextBlob(job).includes('cancel');
}

function isStaleJob(job) {
  if (!['queued', 'running'].includes(job?.status)) return false;
  const stamp = parseJobTime(job.heartbeat_at || job.started_at || job.created_at);
  if (!stamp) return false;
  return Date.now() - stamp > 10 * 60 * 1000;
}

function jobKind(job) {
  if (job?.status === 'done') return 'completed';
  if (['queued', 'running'].includes(job?.status)) return isStaleJob(job) ? 'warning' : 'running';
  if (isCancelledJob(job) || isInterruptedJob(job)) return 'warning';
  if (job?.status === 'failed') return 'error';
  return 'warning';
}

function jobKindLabel(kind, t) {
  return {
    all: t.allJobs,
    running: t.normalJobs || t.runningJobs,
    warning: t.warningJobs,
    error: t.errorJobs,
    completed: t.completedJobs,
  }[kind] || kind;
}

function jobDiagnostic(job, t) {
  if (isStaleJob(job)) return t.jobStaleHint;
  if (isInterruptedJob(job)) return t.jobInterruptedHint;
  if (isCancelledJob(job)) return t.jobCancelledHint;
  return job?.message || job?.stderr || job?.stdout || job?.created_at || '';
}

function jobStageLabel(stage, t) {
  if (!stage) return '-';
  const stageToCommand = {
    'filename-analysis': 'analyze-filenames',
    'keyword-classification': 'classify-keywords',
    'apply-move-plan': 'apply',
    normalize: 'normalize-organized',
    'review-cleanup': 'organize-review',
    'face-report': 'face-cluster-report',
    dedupe: 'dedupe-organized',
    'index-vision': 'index-vision',
    'index-similarity': 'index-similarity',
    'index-metadata': 'index-metadata',
    'metadata-backfill': 'metadata-backfill',
    'thumbnail-repair': 'repair-thumbnails',
    transcribe: 'transcribe',
    'model-download': 'model-pull-recommended',
  };
  return t.commandNames?.[stageToCommand[stage] || stage] || stage;
}

function jobWorkflowInfo(job, t) {
  const steps = workflowSteps[job?.command] || [];
  if (!steps.length) return null;
  const currentStage = job?.stage || '';
  const index = Math.max(0, steps.findIndex(stage => stage === currentStage));
  const doneIndex = job?.status === 'done' ? steps.length - 1 : index;
  const stepNumber = Math.min(steps.length, doneIndex + 1);
  const remaining = job?.status === 'done' ? 0 : Math.max(0, steps.length - stepNumber);
  return {
    stepNumber,
    totalSteps: steps.length,
    remaining,
    currentStage,
    label: jobStageLabel(currentStage, t),
  };
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

function AppLogo({ size = 42 }) {
  return (
    <svg className="appLogo" width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="TG Media Manager logo">
      <defs>
        <linearGradient id="tgmmLogoGradient" x1="8" y1="7" x2="42" y2="42" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#7c8cff" />
          <stop offset=".52" stopColor="#4fa9ff" />
          <stop offset="1" stopColor="#5ee6cf" />
        </linearGradient>
        <filter id="tgmmLogoGlow" x="-35%" y="-35%" width="170%" height="170%" colorInterpolationFilters="sRGB">
          <feGaussianBlur stdDeviation="3.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect x="4" y="4" width="40" height="40" rx="12" fill="url(#tgmmLogoGradient)" filter="url(#tgmmLogoGlow)" />
      <path d="M15 18.5c0-2 1.6-3.5 3.5-3.5h11c1.9 0 3.5 1.5 3.5 3.5v11c0 2-1.6 3.5-3.5 3.5h-11c-1.9 0-3.5-1.5-3.5-3.5v-11Z" fill="none" stroke="white" strokeWidth="2.7" />
      <path d="M20 24h8M24 20v8" stroke="white" strokeWidth="2.7" strokeLinecap="round" />
      <path d="M14 23h-3.5M37.5 23H34M14 27h-3.5M37.5 27H34" stroke="white" strokeWidth="2.4" strokeLinecap="round" opacity=".82" />
    </svg>
  );
}

function Brand({ version, t, showBuild = false }) {
  const build = buildLabel(version, t);
  return (
    <div className="brand">
      <div className="brandMark"><AppLogo /></div>
      <div>
        <strong>TG Media Manager</strong>
        <small title={build}>{displayVersion(version)}{showBuild && build ? ` ${build}` : ''}</small>
      </div>
    </div>
  );
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

function shortenTagLabel(value, max = 8) {
  const text = String(value || '');
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
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

function MediaThumbImage({ item, className = 'mediaThumb', label = '', priority = false }) {
  const [aspect, setAspect] = useState(initialAspect(item));
  const [failed, setFailed] = useState(false);
  const badge = label || (item.media_type === 'video' ? 'VID' : 'IMG');
  const revision = encodeURIComponent(item.updated_at || item.hash8 || item.mtime || '');
  const thumbRevision = `${revision}-${THUMBNAIL_REVISION}`;
  const durationLabel = item.media_type === 'video' && Number(item.duration || 0) > 0 ? formatSeconds(item.duration) : '';
  const resolutionLabel = mediaResolutionLabel(item);
  const isFavorite = Boolean(Number(item.favorite || 0));
  return (
    <div className={className} style={{ '--thumb-ratio': String(aspect) }}>
      {!failed ? (
        <img
          src={`/api/media/${item.id}/thumbnail?v=${thumbRevision}`}
          alt={item.filename}
          loading={priority ? 'eager' : 'lazy'}
          decoding="async"
          fetchPriority={priority ? 'high' : 'auto'}
          onLoad={event => {
            const img = event.currentTarget;
            if (img.naturalWidth && img.naturalHeight) {
              setAspect(Math.max(0.38, Math.min(3.2, img.naturalWidth / img.naturalHeight)));
            }
          }}
          onError={() => setFailed(true)}
        />
      ) : <div className="thumbFallback">{badge}</div>}
      <span className="thumbKind">{badge}</span>
      {(durationLabel || resolutionLabel || isFavorite) && (
        <div className="thumbBadges" aria-hidden="true">
          {resolutionLabel && <span className="thumbBadge thumbResolution">{resolutionLabel}</span>}
          {durationLabel && <span className="thumbBadge thumbDuration">{durationLabel}</span>}
          {isFavorite && <span className="thumbBadge thumbFavorite"><Heart size={13} fill="currentColor" /></span>}
        </div>
      )}
    </div>
  );
}

function LoginScreen({ login, error, theme, setTheme, t, version }) {
  const [password, setPassword] = useState('');
  return (
    <main className="loginShell">
      <section className="loginPanel">
        <Brand version={version} t={t} showBuild />
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
  const [active, setActive] = useState('quickFind');
  const [busy, setBusy] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobLog, setJobLog] = useState(null);
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [results, setResults] = useState([]);
  const [mediaResults, setMediaResults] = useState({ total: 0, items: [] });
  const [randomResults, setRandomResults] = useState({ total: 0, items: [] });
  const [mediaFilters, setMediaFilters] = useState(DEFAULT_MEDIA_FILTERS);
  const [savedSearches, setSavedSearches] = useState([]);
  const [similarityResults, setSimilarityResults] = useState({ groups: [] });
  const [tagGraph, setTagGraph] = useState({ nodes: [], edges: [] });
  const [diagnostics, setDiagnostics] = useState(null);
  const [authors, setAuthors] = useState([]);
  const [faces, setFaces] = useState([]);
  const [faceSuggestions, setFaceSuggestions] = useState([]);
  const [settings, setSettings] = useState(null);
  const [models, setModels] = useState({ root: '/models', models: [] });
  const [modelDrafts, setModelDrafts] = useState({});
  const [manifestDraft, setManifestDraft] = useState('');
  const [monitor, setMonitor] = useState(null);
  const [directories, setDirectories] = useState([]);
  const [browsePath, setBrowsePath] = useState('/media');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [cancelingJobId, setCancelingJobId] = useState(null);
  const modelDraftDirtyRef = useRef(false);
  const manifestDraftDirtyRef = useRef(false);
  const [auth, setAuth] = useState({ enabled: false, authenticated: true, local_only: true });
  const [version, setVersion] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [language, setLanguage] = useState(() => localStorage.getItem('language') || 'zh-CN');
  const [mediaZoom, setMediaZoom] = useState(() => {
    const value = Number(localStorage.getItem('mediaZoom') || 280);
    return Number.isFinite(value) ? Math.max(180, Math.min(420, value)) : 280;
  });
  const t = i18n[language] || i18n['zh-CN'];

  async function refresh() {
    const [s, j, a, f, suggestions, cfg, mon, modelCatalog, ver, diag, saved] = await Promise.all([
      api('/api/summary'),
      api('/api/jobs?limit=120'),
      api('/api/authors').catch(() => []),
      api('/api/face-groups').catch(() => []),
      api('/api/face-merge-suggestions').catch(() => []),
      api('/api/settings').catch(() => null),
      api('/api/monitor').catch(() => null),
      api('/api/models').catch(() => ({ root: '/models', models: [] })),
      api('/api/version').catch(() => null),
      api('/api/diagnostics').catch(() => null),
      api('/api/saved-searches').catch(() => []),
    ]);
    setSummary(s);
    setJobs(j);
    setAuthors(a);
    setFaces(f);
    setFaceSuggestions(suggestions);
    setMonitor(mon);
    setModels(modelCatalog);
    if (diag) setDiagnostics(diag);
    setSavedSearches(saved || []);
    if (!manifestDraftDirtyRef.current) setManifestDraft(modelCatalog?.manifest_url || '');
    if (!modelDraftDirtyRef.current) setModelDrafts(Object.fromEntries((modelCatalog?.models || []).map(model => [model.id, { url: model.source_url || '', sha256: model.sha256 || '' }])));
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
    localStorage.setItem('mediaZoom', String(mediaZoom));
  }, [mediaZoom]);

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
  }, []);

  useEffect(() => {
    if (!auth.authenticated) return undefined;
    const id = setInterval(() => refresh().catch(() => {}), 4000);
    return () => clearInterval(id);
  }, [auth.authenticated]);

  useEffect(() => {
    if (!auth.authenticated || active !== 'jobs' || !selectedJob?.id) return undefined;
    const id = setInterval(() => openJob(selectedJob.id).catch(() => {}), 4000);
    return () => clearInterval(id);
  }, [auth.authenticated, active, selectedJob?.id]);

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

  async function lockPrivacy() {
    setSelectedJob(null);
    setJobLog(null);
    setQuery('');
    setActive('quickFind');
    if (!auth.enabled) return;
    await api('/api/auth/logout', { method: 'POST' }).catch(() => {});
    const status = await api('/api/auth/status').catch(() => ({ enabled: true, authenticated: false, local_only: true }));
    setAuth(status);
  }

  async function start(command) {
    if (jobs.some(job => job.status === 'running' || job.status === 'queued')) {
      setActive('jobs');
      setError(t.runningJobGuard);
      return;
    }
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
    setCancelingJobId(id);
    setError('');
    try {
      await api(`/api/jobs/${id}/cancel`, { method: 'POST' });
      setMessage(t.cancelRequested);
      await refresh();
      await openJob(id);
    } catch (exc) {
      setError(exc.message);
    } finally {
      setCancelingJobId(null);
    }
  }

  async function runSearch(event) {
    event?.preventDefault();
    return performSearch(query, source);
  }

  async function performSearch(nextQuery, nextSource) {
    setError('');
    setSearchLoading(true);
    try {
      const data = await api(`/api/search?q=${encodeURIComponent(nextQuery)}&source=${encodeURIComponent(nextSource)}&limit=200`);
      setResults(data.results);
      setActive('library');
    } catch (exc) {
      setError(exc.message);
    } finally {
      setSearchLoading(false);
    }
  }

  async function loadMedia(params = {}) {
    const filters = {
      q: params.q ?? '',
      media_type: params.media_type ?? 'all',
      tag: params.tag ?? '',
      author: params.author ?? '',
      face_group: params.face_group ?? '',
      favorite: params.favorite ?? '',
      has_subtitles: params.has_subtitles ?? '',
      min_duration: params.min_duration ?? '',
      max_duration: params.max_duration ?? '',
      resolution: params.resolution ?? '',
      semantic: params.semantic ?? '',
    };
    const search = compactSearchParams({
      q: filters.q,
      media_type: filters.media_type,
      tag: filters.tag,
      author: filters.author,
      face_group: filters.face_group,
      favorite: filters.favorite,
      has_subtitles: filters.has_subtitles,
      min_duration: filters.min_duration,
      max_duration: filters.max_duration,
      resolution: filters.resolution,
      semantic: filters.semantic ? 'true' : '',
      randomize: params.randomize ? 'true' : '',
      seed: String(params.seed || 0),
      limit: String(params.limit || 80),
      offset: String(params.offset || 0),
    });
    if (!params.append) setMediaFilters(filters);
    const data = await api(`/api/media?${search.toString()}`);
    if (params.append) {
      let addedCount = 0;
      setMediaResults(current => {
        const existing = current.items || [];
        const seen = new Set(existing.map(item => item.id));
        const added = (data.items || []).filter(item => !seen.has(item.id));
        addedCount = added.length;
        return { ...data, items: [...existing, ...added] };
      });
      return { ...data, added_count: addedCount };
    }
    setMediaResults(data);
    return data;
  }

  async function loadRandomMedia(params = {}) {
    const search = compactSearchParams({
      q: params.q || '',
      media_type: params.media_type || 'all',
      tag: params.tag || '',
      author: params.author || '',
      face_group: params.face_group || '',
      favorite: params.favorite || '',
      has_subtitles: params.has_subtitles || '',
      min_duration: params.min_duration || '',
      max_duration: params.max_duration || '',
      resolution: params.resolution || '',
      randomize: 'true',
      seed: String(params.seed || 0),
      limit: String(params.limit || 80),
      offset: String(params.offset || 0),
    });
    const data = await api(`/api/media?${search.toString()}`);
    if (params.append) {
      let addedCount = 0;
      setRandomResults(current => {
        const currentExisting = current.items || [];
        const currentSeen = new Set(currentExisting.map(item => item.id));
        const currentAdded = (data.items || []).filter(item => !currentSeen.has(item.id));
        addedCount = currentAdded.length;
        return { ...data, items: [...currentExisting, ...currentAdded] };
      });
      return { ...data, added_count: addedCount };
    } else {
      setRandomResults(data);
    }
    return data;
  }

  function removeMediaFromLists(mediaId) {
    const remove = current => {
      const items = (current.items || []).filter(item => item.id !== mediaId);
      const delta = (current.items || []).length - items.length;
      return { ...current, items, total: Math.max(0, Number(current.total || 0) - delta) };
    };
    setMediaResults(remove);
    setRandomResults(remove);
  }

  function patchMediaInLists(media) {
    if (!media?.id) return;
    const patch = current => ({
      ...current,
      items: (current.items || []).map(item => item.id === media.id ? { ...item, ...media } : item),
    });
    setMediaResults(patch);
    setRandomResults(patch);
  }

  async function openFilteredMedia(filters) {
    await loadMedia({ ...DEFAULT_MEDIA_FILTERS, ...filters, limit: 100, offset: 0 });
    setActive('library');
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
    if (!manifestDraftDirtyRef.current) setManifestDraft(data?.manifest_url || '');
    if (!modelDraftDirtyRef.current) setModelDrafts(Object.fromEntries((data?.models || []).map(model => [model.id, { url: model.source_url || '', sha256: model.sha256 || '' }])));
    return data;
  }

  async function saveSearch(name, filters) {
    setError('');
    const saved = await api('/api/saved-searches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, filters }),
    });
    setSavedSearches(current => [saved, ...current]);
    return saved;
  }

  async function deleteSavedSearch(searchId) {
    setError('');
    await api(`/api/saved-searches/${searchId}`, { method: 'DELETE' });
    setSavedSearches(current => current.filter(item => item.id !== searchId));
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

  async function saveModelSource(modelId, draft) {
    setError('');
    try {
      const data = await api('/api/models/source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId, url: draft?.url || '', sha256: draft?.sha256 || '' }),
      });
      modelDraftDirtyRef.current = false;
      setModels(data);
      setMessage(t.modelSourceSaved);
      await loadModels();
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function saveManifestSource(url) {
    setError('');
    try {
      const data = await api('/api/models/manifest-source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url || '' }),
      });
      manifestDraftDirtyRef.current = false;
      setModels(data);
      setManifestDraft(data?.manifest_url || '');
      setMessage(t.modelSourceSaved);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function deleteModel(modelId) {
    const ok = window.confirm(t.deleteModelConfirm);
    if (!ok) return;
    setError('');
    try {
      await api(`/api/models/${encodeURIComponent(modelId)}`, { method: 'DELETE' });
      await loadModels();
      setMessage(t.cacheDeleted);
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
        <Brand version={version} t={t} />
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
            <button className="iconButton" title={t.lockAction} onClick={lockPrivacy}><LockKeyhole size={18} /></button>
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
              openJob={openJob}
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

        {active === 'jobs' && <section className="twoCol jobsLayout"><JobsPanel jobs={jobs} selectedJobId={selectedJob?.id} openJob={openJob} t={t} /><LogPanel selectedJob={selectedJob} jobLog={jobLog} start={start} cancelJob={cancelJob} cancelingJobId={cancelingJobId} hasRunning={hasRunning} busy={busy} setActive={setActive} t={t} /></section>}
        {active === 'quickFind' && <QuickFindPanel mediaResults={mediaResults} mediaFilters={mediaFilters} savedSearches={savedSearches} saveSearch={saveSearch} deleteSavedSearch={deleteSavedSearch} loadMedia={loadMedia} onDeleted={removeMediaFromLists} onPatched={patchMediaInLists} mediaZoom={mediaZoom} setMediaZoom={setMediaZoom} t={t} />}
        {active === 'library' && <LibraryPanel results={results} mediaResults={mediaResults} mediaFilters={mediaFilters} similarityResults={similarityResults} loadMedia={loadMedia} loadSimilarity={loadSimilarity} start={start} performSearch={performSearch} setQuery={setQuery} setSource={setSource} onDeleted={removeMediaFromLists} onPatched={patchMediaInLists} mediaZoom={mediaZoom} setMediaZoom={setMediaZoom} t={t} />}
        {active === 'tagGraph' && <TagGraphPanel graph={tagGraph} loadTagGraph={loadTagGraph} openFilteredMedia={openFilteredMedia} t={t} />}
        {active === 'randomFlow' && <RandomFlowPanel mediaResults={randomResults} loadRandomMedia={loadRandomMedia} onDeleted={removeMediaFromLists} onPatched={patchMediaInLists} mediaZoom={mediaZoom} setMediaZoom={setMediaZoom} t={t} />}
        {active === 'models' && <ModelsPanel catalog={models} drafts={modelDrafts} setDrafts={setModelDrafts} manifestDraft={manifestDraft} setManifestDraft={setManifestDraft} modelDraftDirtyRef={modelDraftDirtyRef} manifestDraftDirtyRef={manifestDraftDirtyRef} saveModelSource={saveModelSource} saveManifestSource={saveManifestSource} pullModel={pullModel} deleteModel={deleteModel} start={start} busy={busy || hasRunning} t={t} />}
        {active === 'diagnostics' && <DiagnosticsPanel diagnostics={diagnostics} refresh={refresh} start={start} busy={busy || hasRunning} t={t} />}
        {active === 'authors' && <AuthorsPanel authors={authors} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} syncAuthors={syncAuthors} onDeleted={removeMediaFromLists} onPatched={patchMediaInLists} mediaZoom={mediaZoom} t={t} />}
        {active === 'faces' && <FaceGroupsPanel faces={faces} suggestions={faceSuggestions} nameFace={nameFace} mergeFace={mergeFace} mergeNamedFaces={mergeNamedFaces} onDeleted={removeMediaFromLists} onPatched={patchMediaInLists} mediaZoom={mediaZoom} t={t} />}
        {active === 'logs' && <LogsPanel jobs={jobs} applied={applied} openJob={openJob} setActive={setActive} t={t} />}
        {active === 'settings' && <SettingsPanel settings={settings} setSettings={setSettings} saveSettings={saveSettings} browse={browse} directories={directories} browsePath={browsePath} monitor={monitor} checkMonitorNow={checkMonitorNow} t={t} />}
      </section>
    </main>
  );
}

function BucketPanel({ title, rows }) {
  return <div className="panel"><div className="panelHead"><h2>{title}</h2><span>{rows.length}</span></div><div className="list">{rows.map(item => <div className="row" key={item.name}><span>{item.name}</span><strong>{item.files}</strong></div>)}</div></div>;
}

function DashboardPanel({ summary, jobs, mediaResults, tagGraph, loadMedia, openJob, setActive, t }) {
  const top = summary?.top || {};
  const keywords = summary?.keywords || [];
  const actors = summary?.actors_sample || [];
  const runningJobs = jobs.filter(job => job.status === 'running' || job.status === 'queued');
  const items = (mediaResults.items || []).slice(0, 6);
  const mediaTotal = estimatedMediaTotal(summary, mediaResults);
  const videoCount = summary?.media_types?.video ?? mediaResults.video_total ?? 0;
  const photoCount = summary?.media_types?.photo ?? mediaResults.photo_total ?? 0;
  const stats = [
    [t.totalMedia, mediaTotal, FolderOpen, 'blue', `${t.videos} ${prettyNumber(videoCount)} / ${t.photos} ${prettyNumber(photoCount)}`, () => setActive('library')],
    [t.totalTags, keywords.length || top.keywords, Tags, 'purple', `${t.keywords} ${prettyNumber(top.keywords || 0)}`, () => setActive('tagGraph')],
    [t.totalAuthors, actors.length || top.actors, Users, 'green', `${t.actors} ${prettyNumber(top.actors || 0)}`, () => setActive('authors')],
    [t.faces, top.faces || summary?.vision?.face_group_rows || 0, ScanFace, 'orange', `${t.faceRows} ${prettyNumber(summary?.vision?.face_index_rows || 0)}`, () => setActive('faces')],
    [t.taskRunning, runningJobs.length, CheckCircle2, 'blue', `${t.jobs} ${prettyNumber(jobs.length)}`, () => setActive('jobs')],
  ];
  return (
    <>
      <section className="dashboardStats">
        {stats.map(([label, value, Icon, tone, sub, onClick]) => <Stat key={label} label={label} value={prettyNumber(value)} icon={Icon} tone={tone} sub={sub} onClick={onClick} />)}
      </section>
      <section className="dashboardMain">
        <DashboardTagGraph graph={tagGraph} keywords={keywords} loadMedia={loadMedia} setActive={setActive} t={t} />
        <RecentMediaPanel items={items} total={mediaResults.total || items.length} setActive={setActive} t={t} />
      </section>
      <section className="dashboardBottom">
        <DashboardJobs jobs={jobs} openJob={openJob} setActive={setActive} t={t} />
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

function DashboardJobs({ jobs, openJob, setActive, t }) {
  const rows = jobs.slice(0, 4);
  return (
    <section className="panel taskPanel">
      <div className="panelHead"><h2>{t.taskList}</h2><button className="softLink" onClick={() => setActive('jobs')}>{t.viewAllTasks}</button></div>
      {!rows.length ? <Empty label={t.noRows} /> : <div className="taskRows">{rows.map(job => {
        const progress = job.status === 'done' ? 100 : job.status === 'running' ? 66 : job.status === 'queued' ? 28 : 0;
        return (
          <button className="taskRow" key={job.id} onClick={() => { openJob(job.id); setActive('jobs'); }}>
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
  const storage = summary?.media_storage || {};
  const videos = {
    count: Number(storage.video?.count ?? summary?.media_types?.video ?? 0),
    bytes: Number(storage.video?.bytes || 0),
  };
  const photos = {
    count: Number(storage.photo?.count ?? summary?.media_types?.photo ?? 0),
    bytes: Number(storage.photo?.bytes || 0),
  };
  const fallbackOtherCount = Math.max(0, Number(mediaTotal || 0) - videos.count - photos.count);
  const other = {
    count: Number(storage.other?.count ?? fallbackOtherCount),
    bytes: Number(storage.other?.bytes || 0),
  };
  const totalBytes = videos.bytes + photos.bytes + other.bytes;
  const totalCount = videos.count + photos.count + other.count;
  const ringTotal = totalBytes > 0 ? totalBytes : Math.max(1, totalCount || mediaTotal || 1);
  const videoValue = totalBytes > 0 ? videos.bytes : videos.count;
  const photoValue = totalBytes > 0 ? photos.bytes : photos.count;
  const otherValue = totalBytes > 0 ? other.bytes : other.count;
  const videoPct = Math.max(0, Math.round((videoValue / ringTotal) * 100));
  const photoPct = Math.max(0, Math.round((photoValue / ringTotal) * 100));
  const otherPct = Math.max(0, Math.round((otherValue / ringTotal) * 100));
  const formatStorage = (item, unit) => {
    const countText = `${prettyNumber(item.count)} ${unit}`;
    if (totalBytes <= 0) return countText;
    return t.locale === 'zh-CN'
      ? `${prettyBytes(item.bytes)}（${countText}）`
      : `${prettyBytes(item.bytes)} (${countText})`;
  };
  return (
    <section className="panel storagePanel">
      <div className="panelHead"><h2>{t.storageSpace}</h2><span>{t.localOnly}</span></div>
      <div className="storageBody">
        <div className="storageRing" style={{ '--video': `${videoPct}%`, '--photo': `${photoPct}%`, '--other': `${otherPct}%` }}><HardDrive size={24} /><strong>{totalBytes > 0 ? prettyBytes(totalBytes) : prettyNumber(mediaTotal)}</strong><span>{totalBytes > 0 ? t.totalCapacity : t.usedSpace}</span></div>
        <div className="storageList">
          <div><i className="violet" /><span>{t.videoFiles}</span><strong>{formatStorage(videos, t.videoUnit)}</strong></div>
          <div><i className="pink" /><span>{t.imageFiles}</span><strong>{formatStorage(photos, t.photoUnit)}</strong></div>
          <div><i className="blue" /><span>{t.otherFiles}</span><strong>{formatStorage(other, t.itemUnit)}</strong></div>
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
  const processed = Number(job.processed || 0);
  const total = Number(job.total || 0);
  const derived = total > 0 ? Math.floor((processed / total) * 100) : 0;
  if (job.status === 'done') return 100;
  return Math.max(0, Math.min(100, Math.max(value, derived)));
}

function JobsPanel({ jobs, selectedJobId, openJob, t }) {
  const [filter, setFilter] = useState('all');
  const sorted = sortJobsNewest(jobs);
  const filters = ['all', 'running', 'warning', 'error', 'completed'];
  const counts = filters.reduce((acc, key) => {
    acc[key] = key === 'all' ? sorted.length : sorted.filter(job => jobKind(job) === key).length;
    return acc;
  }, {});
  const filtered = filter === 'all' ? sorted : sorted.filter(job => jobKind(job) === filter);
  const groups = [
    ['running', filtered.filter(job => jobKind(job) === 'running')],
    ['warning', filtered.filter(job => jobKind(job) === 'warning')],
    ['error', filtered.filter(job => jobKind(job) === 'error')],
    ['completed', filtered.filter(job => jobKind(job) === 'completed')],
    ['other', filtered.filter(job => !['running', 'warning', 'error', 'completed'].includes(jobKind(job)))],
  ].filter(([, rows]) => rows.length);
  return <div className="panel"><div className="panelHead"><h2>{t.jobs}</h2><span>{jobs.length}</span></div>
    <div className="statusTabs" role="tablist" aria-label={t.jobs}>
      {filters.map(key => <button key={key} className={filter === key ? 'active' : ''} onClick={() => setFilter(key)}>{jobKindLabel(key, t)}<span>{counts[key] || 0}</span></button>)}
    </div>
    <div className="hintBox compact"><span>{t.jobHistoryHint}</span></div>
    <div className="jobGroups">{groups.map(([kind, rows]) => (
    <section className="jobGroup" key={kind}>
      <div className="jobGroupHead"><strong>{kind === 'other' ? t.otherJobs : jobKindLabel(kind, t)}</strong><span>{rows.length}</span></div>
      <div className="jobs">{rows.map(job => {
        const pct = jobPercent(job);
        const processed = Number(job.processed || 0);
        const total = Number(job.total || 0);
        const workflow = jobWorkflowInfo(job, t);
        const kind = jobKind(job);
        const diagnostic = jobDiagnostic(job, t);
        return (
          <button className={`job ${kind} ${selectedJobId === job.id ? 'selected' : ''}`} key={job.id} data-job-id={job.id} data-job-kind={kind} onClick={() => openJob(job.id)}>
            <div className="jobMain">
              <strong>#{job.id} {t.commandNames?.[job.command] || job.command}</strong>
              <p>{workflow ? `${workflow.label} · ${t.workflowStep} ${workflow.stepNumber}/${workflow.totalSteps} · ${t.remainingSteps} ${workflow.remaining}` : (job.stage || job.message || job.created_at)}</p>
              {diagnostic && kind !== 'running' && <small className="jobDiagnostic">{diagnostic}</small>}
              {job.current_item && <small>{job.current_item}</small>}
              <i className="jobProgress"><b style={{ width: `${pct}%` }} /></i>
              <small>{t.currentStepProgress}: {pct}% {total ? `${processed}/${total}` : ''} {Number(job.failed_count || 0) ? `${t.failedShort} ${job.failed_count}` : ''}</small>
            </div>
            <JobBadge status={job.status} kind={kind} label={jobKindLabel(kind, t)} />
          </button>
        );
      })}</div>
    </section>
  ))}</div></div>;
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

function LogPanel({ selectedJob, jobLog, start, cancelJob, cancelingJobId, hasRunning, busy, setActive, t }) {
  const next = selectedJob ? jobNextStep(selectedJob.command, t) : '';
  const actions = selectedJob ? jobNextActions(selectedJob.command, t, start, setActive) : [];
  const canStop = selectedJob && ['queued', 'running'].includes(selectedJob.status);
  const canResume = selectedJob && ['cancelled', 'failed'].includes(selectedJob.status);
  const isCanceling = selectedJob && cancelingJobId === selectedJob.id;
  const canRetryFrames = selectedJob && ['failed', 'cancelled'].includes(selectedJob.status) && (
    String(selectedJob.command || '').includes('extract-frames') ||
    String(selectedJob.stage || '').includes('frame') ||
    String(jobLog?.stdout || '').toLowerCase().includes('frame') ||
    String(jobLog?.stderr || '').toLowerCase().includes('frame')
  );
  const pct = selectedJob ? jobPercent(selectedJob) : 0;
  const workflow = selectedJob ? jobWorkflowInfo(selectedJob, t) : null;
  const kind = selectedJob ? jobKind(selectedJob) : '';
  const diagnostic = selectedJob ? jobDiagnostic(selectedJob, t) : '';
  return <div className="panel"><div className="panelHead"><h2>{selectedJob ? `Job #${selectedJob.id}` : t.jobLog}</h2><span>{selectedJob?.status || t.selectJob}</span></div>{!selectedJob ? <Empty label={t.selectJobHint} /> : <div className="logBlock">
    <div className="jobDetailHero">
      <strong>{pct}%</strong>
      <i className="jobProgress"><b style={{ width: `${pct}%` }} /></i>
      <span>{workflow ? `${workflow.label} · ${t.workflowStep} ${workflow.stepNumber}/${workflow.totalSteps} · ${t.remainingSteps} ${workflow.remaining}` : (selectedJob.stage || selectedJob.message || '-')}</span>
    </div>
    {diagnostic && kind !== 'running' && <div className={`hintBox compact ${kind}`}><span>{diagnostic}</span></div>}
    <div className="nextActions">
      {canStop && <button disabled={isCanceling} onClick={() => cancelJob(selectedJob.id)}><Archive size={15} />{isCanceling ? t.cancelRequested : (t.stopJob || 'Stop')}</button>}
      {canResume && <button disabled={busy || hasRunning} onClick={() => start(selectedJob.command)}><Play size={15} />{t.resumeJob || 'Resume'}</button>}
      {canRetryFrames && <button disabled={busy || hasRunning} onClick={() => start('extract-frames-retry-failed')}><RefreshCw size={15} />{t.commandNames?.['extract-frames-retry-failed'] || 'Retry Frames'}</button>}
    </div>
    <div className="list" data-job-detail={selectedJob.id}>
      <div className="row"><span>{t.command}</span><strong>{selectedJob.command}</strong></div>
      <div className="row"><span>status</span><strong>{jobKindLabel(kind, t)} · {selectedJob.status}</strong></div>
      <div className="row"><span>stage</span><strong>{selectedJob.stage || '-'}</strong></div>
      {workflow && <div className="row"><span>{t.workflowProgress}</span><strong>{workflow.stepNumber}/{workflow.totalSteps} · {t.remainingSteps} {workflow.remaining}</strong></div>}
      <div className="row"><span>processed</span><strong>{selectedJob.processed || 0}/{selectedJob.total || 0}</strong></div>
      <div className="row"><span>current</span><strong>{selectedJob.current_item || '-'}</strong></div>
      <div className="row"><span>failed/skipped</span><strong>{selectedJob.failed_count || 0}/{selectedJob.skipped_count || 0}</strong></div>
      <div className="row"><span>heartbeat</span><strong>{formatDateTime(selectedJob.heartbeat_at)}</strong></div>
      <div className="row"><span>{t.started}</span><strong>{formatDateTime(selectedJob.started_at)}</strong></div>
      <div className="row"><span>{t.finished}</span><strong>{formatDateTime(selectedJob.finished_at)}</strong></div>
    </div>
    {next && <div className="hintBox"><strong>{t.jobNextStep}</strong><span>{next}</span>{actions.length > 0 && <div className="nextActions">{actions.map(([label, action]) => <button key={label} disabled={busy || hasRunning} onClick={action}><Play size={15} />{label}</button>)}</div>}</div>}
    <h3>stdout</h3><pre>{jobLog?.stdout || '(empty)'}</pre><h3>stderr</h3><pre>{jobLog?.stderr || '(empty)'}</pre></div>}</div>;
}

function TagGraphPanel({ graph, loadTagGraph, openFilteredMedia, t }) {
  const [minEdge, setMinEdge] = useState(2);
  const [focusedTag, setFocusedTag] = useState('');
  const [draggingTag, setDraggingTag] = useState('');
  const [manualPositions, setManualPositions] = useState({});
  const [hoverPoint, setHoverPoint] = useState(null);
  const [zoom, setZoom] = useState(1);
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const topNodes = nodes.slice(0, 42);
  const maxCount = Math.max(...topNodes.map(node => Number(node.media_count || 0)), 1);
  const positions = useMemo(() => new Map(topNodes.map((node, index) => {
    if (manualPositions[node.tag]) return [node.tag, manualPositions[node.tag]];
    if (index === 0) return [node.tag, { x: 50, y: 50 }];
    const golden = Math.PI * (3 - Math.sqrt(5));
    const ring = Math.ceil(Math.sqrt(index));
    const angle = index * golden;
    const radius = Math.min(39, 12 + ring * 6.2 + (index % 3) * 1.9);
    return [node.tag, {
      x: Math.max(8, Math.min(92, 50 + Math.cos(angle) * radius)),
      y: Math.max(10, Math.min(90, 50 + Math.sin(angle) * radius * .78)),
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
    openFilteredMedia({ tag: secondTag ? `${tag},${secondTag}` : tag });
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
                const normalized = Math.sqrt(Number(node.media_count || 0) / maxCount);
                const size = 3.2 + normalized * 7.2;
                const fontSize = Math.max(1.25, Math.min(2.55, size * .28));
                const countSize = Math.max(1, fontSize * .72);
                const classes = [focusedTag === node.tag ? 'isFocused' : '', nodeIsDimmed(node.tag) ? 'isDimmed' : ''].filter(Boolean).join(' ');
                return (
                  <g className={classes} key={node.tag} onClick={() => setFocusedTag(node.tag)} onDoubleClick={() => openTag(node.tag)} onPointerDown={event => { event.currentTarget.setPointerCapture?.(event.pointerId); setDraggingTag(node.tag); }}>
                    <circle cx={point.x} cy={point.y} r={size} />
                    <text className="nodeLabel" x={point.x} y={point.y - (Number(node.media_count || 0) ? countSize * .28 : 0)} style={{ fontSize: `${fontSize}px` }}>
                      <title>{node.tag}</title>
                      {shortenTagLabel(node.tag, size > 8 ? 9 : 7)}
                    </text>
                    {Number(node.media_count || 0) > 0 && <text className="nodeCount" x={point.x} y={point.y + fontSize * .92} style={{ fontSize: `${countSize}px` }}>{prettyNumber(node.media_count)}</text>}
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

function QuickFindPanel({ mediaResults, mediaFilters, savedSearches, saveSearch, deleteSavedSearch, loadMedia, onDeleted, onPatched, mediaZoom, setMediaZoom, t }) {
  const [filters, setFilters] = useState({ ...DEFAULT_MEDIA_FILTERS, semantic: 'true', ...(mediaFilters || {}) });
  const [saveName, setSaveName] = useState('');
  const [loading, setLoading] = useState(false);
  const [panelError, setPanelError] = useState('');
  const [saving, setSaving] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [recentSearches, setRecentSearches] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('recentSmartSearches') || '[]');
    } catch {
      return [];
    }
  });
  useEffect(() => {
    const text = String(filters.q || '').trim();
    if (!text) {
      setParsed(null);
      return undefined;
    }
    const controller = new AbortController();
    const id = setTimeout(() => {
      api(`/api/search/parse?${compactSearchParams({ q: text })}`, { signal: controller.signal })
        .then(data => setParsed(data.parsed || null))
        .catch(exc => {
          if (exc.name !== 'AbortError') setParsed(null);
        });
    }, 220);
    return () => {
      clearTimeout(id);
      controller.abort();
    };
  }, [filters.q]);
  function rememberSearch(text) {
    const trimmed = String(text || '').trim();
    if (!trimmed) return;
    const next = [trimmed, ...recentSearches.filter(item => item !== trimmed)].slice(0, 8);
    setRecentSearches(next);
    localStorage.setItem('recentSmartSearches', JSON.stringify(next));
  }
  function effectiveFilters(base = filters) {
    const p = parsed || {};
    return {
      ...base,
      media_type: base.media_type && base.media_type !== 'all' ? base.media_type : (p.media_type || base.media_type || 'all'),
      tag: base.tag || '',
      author: base.author || p.author || '',
      face_group: base.face_group || p.face_group || '',
      favorite: base.favorite || p.favorite || '',
      has_subtitles: base.has_subtitles || p.has_subtitles || '',
      min_duration: base.min_duration || p.min_duration || '',
      max_duration: base.max_duration || p.max_duration || '',
      resolution: base.resolution || p.resolution || '',
      semantic: base.semantic || 'true',
    };
  }
  async function run(event) {
    event?.preventDefault();
    setPanelError('');
    setLoading(true);
    try {
      const next = effectiveFilters();
      setFilters(next);
      rememberSearch(next.q);
      await loadMedia({ ...next, limit: 96, offset: 0 });
    } catch (exc) {
      setPanelError(exc.message);
    } finally {
      setLoading(false);
    }
  }
  function update(key, value) {
    setFilters(current => ({ ...current, [key]: value }));
  }
  function applySemanticPreset(value) {
    const text = String(value || '').trim();
    const next = { ...filters, q: text, semantic: filters.semantic || 'true' };
    const durationMatch = text.match(/(\d+)\s*(?:分钟|min).*?(以上|大于|超过|\+)/);
    if (durationMatch) next.min_duration = String(Number(durationMatch[1]) * 60);
    if (/4k|2160/i.test(text)) next.resolution = '4K';
    if (/1080/.test(text)) next.resolution = '1080';
    const tagTerms = ['室内', '户外', '制服', '水手服', '露脸', '自拍', 'COS', 'JK', '黑丝', '白丝'].filter(term => text.includes(term));
    if (tagTerms.length) next.tag = tagTerms.join(',');
    setFilters(next);
  }
  async function saveCurrentSearch() {
    const name = saveName.trim() || [filters.q, filters.tag, filters.author, filters.face_group].filter(Boolean).join(' / ') || t.savedSearch;
    setSaving(true);
    setPanelError('');
    try {
      await saveSearch(name, effectiveFilters());
      setSaveName('');
    } catch (exc) {
      setPanelError(exc.message);
    } finally {
      setSaving(false);
    }
  }
  const shortcuts = [
    '找 10 分钟以上 室内 制服 露脸的视频',
    '找 4K COS 角色 图片',
    '有字幕的视频',
    '自拍露脸 黑丝白丝',
    '户外 露出 短视频',
  ];
  const parsedItems = parsed?.explain || [];
  return (
    <section className="panel quickFindPanel smartSearchPanel">
      <div className="panelHead smartHero">
        <div><h2>{t.quickFindTitle}</h2><p>{t.quickFindHint}</p></div>
        <MediaZoomControl value={mediaZoom} setValue={setMediaZoom} t={t} />
      </div>
      <form className="quickFindForm smartSearchForm" onSubmit={run}>
        <input className="quickFindInput" value={filters.q} onChange={event => applySemanticPreset(event.target.value)} placeholder={t.mediaSearch} autoComplete="off" />
        <button type="submit" disabled={loading}><Search size={16} />{loading ? t.loadingMore : t.searchNow}</button>
      </form>
      <div className="smartSearchMeta">
        <label className="inlineCheck"><input type="checkbox" checked={!!filters.semantic} onChange={event => update('semantic', event.target.checked ? 'true' : '')} />{t.semanticMode}</label>
        <span>{t.semanticFallbackHint}</span>
      </div>
      {!!parsedItems.length && <div className="parsedBox"><strong>{t.understoodQuery}</strong>{parsedItems.map(item => <span key={item}>{item}</span>)}</div>}
      <div className="quickChips suggestionChips">
        {shortcuts.map(value => <button key={value} type="button" onClick={() => { applySemanticPreset(value); }}>{value}</button>)}
      </div>
      <details className="quickAdvanced">
        <summary>{t.advancedFilters}</summary>
        <div className="quickFindForm compactFilters">
          <select value={filters.media_type} onChange={event => update('media_type', event.target.value)}>
            <option value="all">{t.allMedia}</option>
            <option value="photo">{t.photosOnly}</option>
            <option value="video">{t.videosOnly}</option>
          </select>
          <input value={filters.tag} onChange={event => update('tag', event.target.value)} placeholder={t.tags} />
          <input value={filters.author} onChange={event => update('author', event.target.value)} placeholder={t.authorName} />
          <input value={filters.face_group} onChange={event => update('face_group', event.target.value)} placeholder={t.faceGroupFilter} />
          <select value={filters.favorite} onChange={event => update('favorite', event.target.value)}>
            <option value="">{t.favoriteAny}</option>
            <option value="true">{t.favoriteOnly}</option>
            <option value="false">{t.favoriteExclude}</option>
          </select>
          <select value={filters.has_subtitles} onChange={event => update('has_subtitles', event.target.value)}>
            <option value="">{t.subtitleAny}</option>
            <option value="true">{t.subtitleOnly}</option>
            <option value="false">{t.subtitleMissing}</option>
          </select>
          <input type="number" min="0" value={filters.min_duration} onChange={event => update('min_duration', event.target.value)} placeholder={t.minDurationSeconds} />
          <input type="number" min="0" value={filters.max_duration} onChange={event => update('max_duration', event.target.value)} placeholder={t.maxDurationSeconds} />
          <input value={filters.resolution} onChange={event => update('resolution', event.target.value)} placeholder={t.resolutionFilter} />
        </div>
      </details>
      <div className="savedSearchBox">
        <div className="saveSearchForm">
          <input value={saveName} onChange={event => setSaveName(event.target.value)} placeholder={t.savedSearchName} />
          <button className="panelButton" type="button" disabled={saving} onClick={saveCurrentSearch}><Save size={16} />{t.saveSearch}</button>
        </div>
        {!!recentSearches.length && <div className="savedSearchList recentSearchList"><strong>{t.recentSearches}</strong>
          {recentSearches.map(item => <button type="button" className="recentSearchChip" key={item} onClick={() => { applySemanticPreset(item); loadMedia({ ...filters, q: item, semantic: 'true', limit: 96, offset: 0 }).catch(exc => setPanelError(exc.message)); }}>{item}</button>)}
        </div>}
        {!!savedSearches?.length && <div className="savedSearchList">
          {savedSearches.map(item => (
            <span className="savedSearchChip" key={item.id}>
              <button type="button" onClick={() => { const next = { ...DEFAULT_MEDIA_FILTERS, ...(item.filters || {}) }; setFilters(next); loadMedia({ ...next, limit: 96, offset: 0 }).catch(exc => setPanelError(exc.message)); }}>{item.name}</button>
              <button type="button" title={t.deleteModel} onClick={() => deleteSavedSearch(item.id).catch(exc => setPanelError(exc.message))}><XCircle size={13} /></button>
            </span>
          ))}
        </div>}
      </div>
      {panelError && <div className="alert compact">{panelError}</div>}
      <div className="panelHead compactHead"><h2>{t.searchResults}</h2><span>{prettyNumber(mediaResults.total || 0)}</span></div>
      <MediaGrid items={mediaResults.items || []} onDeleted={onDeleted} onPatched={onPatched} mediaZoom={mediaZoom} t={t} />
    </section>
  );
}

function DiagnosticsPanel({ diagnostics, refresh, start, busy, t }) {
  const coverage = diagnostics?.coverage || [];
  const recommendations = diagnostics?.recommendations || [];
  const thumb = diagnostics?.thumbnail_health || {};
  const privacy = diagnostics?.privacy || {};
  const missingModels = diagnostics?.models?.missing || [];
  const failures = diagnostics?.recent_failed_jobs || [];
  return (
    <>
      <section className="panel diagnosticsHero">
        <div>
          <h2>{t.diagnosticsTitle}</h2>
          <p>{t.diagnosticsHint}</p>
        </div>
        <button className="panelButton" onClick={refresh}><RefreshCw size={16} />{t.refreshState || t.ready}</button>
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.localRuntimeStatus}</h2><span>{privacy.local_only ? t.localOnly : 'remote'}</span></div>
        <div className="diagnosticsGrid">
          <article className="diagnosticCard"><div className="diagnosticTop"><strong>{t.mediaRoot}</strong><span>{privacy.media_root || diagnostics?.root || '-'}</span></div><p>{t.localOnly}</p></article>
          <article className="diagnosticCard"><div className="diagnosticTop"><strong>{t.databasePath}</strong><span>{privacy.database_path || '-'}</span></div><p>SQLite / WAL</p></article>
          <article className="diagnosticCard"><div className="diagnosticTop"><strong>{t.modelRoot}</strong><span>{privacy.model_root || '/models'}</span></div><p>{t.modelHint}</p></article>
          <article className="diagnosticCard"><div className="diagnosticTop"><strong>{t.remoteModels}</strong><span>{privacy.remote_models_enabled ? 'on' : 'off'}</span></div><p>{t.privacyCopy}</p></article>
        </div>
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.coverage}</h2><span>{diagnostics?.generated_at || '-'}</span></div>
        {!coverage.length ? <Empty label={t.noRows} /> : <div className="diagnosticsGrid">
          {coverage.map(item => (
            <article className="diagnosticCard" key={item.id}>
              <div className="diagnosticTop"><strong>{item.label}</strong><span>{item.percent}%</span></div>
              <div className="coverageTrack"><i style={{ width: `${item.percent}%` }} /></div>
              <p>{prettyNumber(item.ready)} / {prettyNumber(item.total)}</p>
              {item.action && <button className="panelButton" disabled={busy} onClick={() => start(item.action)}>{t.runAction}: {t.commandNames?.[item.action] || item.action}</button>}
            </article>
          ))}
        </div>}
      </section>
      <section className="panel">
        <div className="panelHead">
          <div><h2>{t.thumbnailHealth}</h2><p>{t.thumbnailHealthHint}</p></div>
          <button className="panelButton" disabled={busy} onClick={() => start('repair-thumbnails')}><Camera size={16} />{t.commandNames?.['repair-thumbnails'] || 'Repair Thumbnails'}</button>
        </div>
        <div className="diagnosticsGrid">
          {[
            ['cached_files', 'Cached'],
            ['sample_checked', 'Checked'],
            ['sample_healthy', 'Healthy'],
            ['sample_unhealthy', 'Unhealthy'],
            ['sample_missing', 'Missing'],
          ].map(([key, label]) => (
            <article className={`diagnosticCard ${key === 'sample_unhealthy' && Number(thumb[key] || 0) ? 'error' : ''}`} key={key}>
              <div className="diagnosticTop"><strong>{label}</strong><span>{prettyNumber(thumb[key] || 0)}</span></div>
              <p>{thumb.cache || 'media_thumbs_v8'}</p>
            </article>
          ))}
        </div>
        {thumb.error && <div className="hintBox error"><span>{thumb.error}</span></div>}
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.missingModels}</h2><span>{missingModels.length}</span></div>
        {!missingModels.length ? <Empty label={t.ready} /> : <div className="diagnosticsGrid">
          {missingModels.map(model => (
            <article className={`diagnosticCard ${model.recommended ? 'warning' : ''}`} key={model.id}>
              <div className="diagnosticTop"><strong>{model.name || model.id}</strong><span>{model.status}</span></div>
              <p>{model.category}{model.recommended ? ` · ${t.downloadRecommended}` : ''}</p>
            </article>
          ))}
        </div>}
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.recentFailures}</h2><span>{failures.length}</span></div>
        {!failures.length ? <Empty label={t.noFailures} /> : <div className="recommendationList">
          {failures.map(job => (
            <div className="hintBox error" key={job.id}>
              <strong>#{job.id} {t.commandNames?.[job.command] || job.command}</strong>
              <span>{job.stage || job.message || job.stderr || '-'}</span>
            </div>
          ))}
        </div>}
      </section>
      <section className="panel">
        <div className="panelHead"><h2>{t.nextActions}</h2><span>{recommendations.length}</span></div>
        {!recommendations.length ? <Empty label={t.ready} /> : <div className="recommendationList">
          {recommendations.map((item, index) => (
            <div className={`hintBox ${item.level}`} key={`${item.command}-${index}`}>
              <strong>{item.title}</strong>
              <span>{item.detail}</span>
              {item.command && <button className="panelButton" disabled={busy} onClick={() => start(item.command)}>{t.runAction}: {t.commandNames?.[item.command] || item.command}</button>}
            </div>
          ))}
        </div>}
      </section>
    </>
  );
}

function MediaZoomControl({ value, setValue, t }) {
  const zoom = Number(value || 280);
  return (
    <label className="mediaZoomControl" title={`${t.mediaZoom}: ${zoom}px`}>
      <span>{t.smallerCards}</span>
      <input type="range" min="180" max="420" step="10" value={zoom} onChange={event => setValue(Number(event.target.value))} aria-label={t.mediaZoom} />
      <span>{t.largerCards}</span>
    </label>
  );
}

function RandomFlowPanel({ mediaResults, loadRandomMedia, onDeleted, onPatched, mediaZoom, setMediaZoom, t }) {
  const [filters, setFilters] = useState({ media_type: 'all', tag: '', author: '', q: '' });
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [panelError, setPanelError] = useState('');
  const [exhausted, setExhausted] = useState(false);
  const [seed, setSeed] = useState(() => Math.floor(Math.random() * 2147483646) + 1);
  const sentinelRef = useRef(null);
  const activeFilters = [filters.media_type !== 'all' ? filters.media_type : '', filters.q, filters.tag, filters.author].filter(Boolean);
  const items = mediaResults.items || [];
  const hasMore = !exhausted && Number(mediaResults.total || 0) > items.length;
  async function run(event) {
    event?.preventDefault();
    const nextSeed = Math.floor(Math.random() * 2147483646) + 1;
    setSeed(nextSeed);
    setExhausted(false);
    setPanelError('');
    setLoadingSearch(true);
    try {
      await loadRandomMedia({ ...filters, seed: nextSeed });
    } catch (exc) {
      setPanelError(exc.message);
    } finally {
      setLoadingSearch(false);
    }
  }
  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const data = await loadRandomMedia({ ...filters, append: true, limit: 80, offset: items.length, seed });
      if (!data.items?.length || Number(data.added_count || 0) === 0) setExhausted(true);
    } catch (exc) {
      setPanelError(exc.message);
    } finally {
      setLoadingMore(false);
    }
  }
  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) loadMore();
    }, { rootMargin: '800px 0px' });
    const checkNearBottom = () => {
      const remaining = document.documentElement.scrollHeight - window.scrollY - window.innerHeight;
      if (remaining < 1200) loadMore();
    };
    observer.observe(node);
    window.addEventListener('scroll', checkNearBottom, { passive: true });
    window.addEventListener('resize', checkNearBottom);
    window.setTimeout(checkNearBottom, 250);
    const interval = window.setInterval(checkNearBottom, 1000);
    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', checkNearBottom);
      window.removeEventListener('resize', checkNearBottom);
      window.clearInterval(interval);
    };
  }, [items.length, hasMore, loadingMore, filters.media_type, filters.q, filters.tag, filters.author, seed]);
  return (
    <section className="panel">
      <div className="panelHead"><h2>{t.randomFlow}</h2><div className="panelActions"><MediaZoomControl value={mediaZoom} setValue={setMediaZoom} t={t} /><button className="panelButton" onClick={run}><Shuffle size={16} />{t.randomize}</button></div><span>{mediaResults.total || 0}</span></div>
      <form className="mediaSearchBar randomBar" onSubmit={run}>
        <select value={filters.media_type} onChange={event => setFilters({ ...filters, media_type: event.target.value })}>
          <option value="all">{t.allMedia}</option>
          <option value="photo">{t.photosOnly}</option>
          <option value="video">{t.videosOnly}</option>
        </select>
        <input value={filters.q} onChange={event => setFilters({ ...filters, q: event.target.value })} placeholder={t.mediaSearch} />
        <input value={filters.tag} onChange={event => setFilters({ ...filters, tag: event.target.value })} placeholder={t.tags} />
        <input value={filters.author} onChange={event => setFilters({ ...filters, author: event.target.value })} placeholder={t.authorName} />
        <button type="submit" disabled={loadingSearch}><Shuffle size={16} />{loadingSearch ? t.loadingMore : t.randomize}</button>
      </form>
      {activeFilters.length > 0 && <div className="hintBox smallHint"><span>{t.searchResults}: {activeFilters.join(' / ')}</span></div>}
      {panelError && <div className="alert compact">{panelError}</div>}
      <MediaGrid items={items} onDeleted={onDeleted} onPatched={onPatched} mediaZoom={mediaZoom} t={t} />
      <div className="infiniteSentinel" ref={sentinelRef}>{loadingMore ? t.loadingMore : hasMore ? t.scrollForMore : t.noMoreMedia}</div>
    </section>
  );
}

function LibraryPanel({ results, mediaResults, mediaFilters, similarityResults, loadMedia, loadSimilarity, start, performSearch, setQuery, setSource, onDeleted, onPatched, mediaZoom, setMediaZoom, t }) {
  const [mediaQuery, setMediaQuery] = useState(mediaFilters.q || '');
  const [mediaType, setMediaType] = useState(mediaFilters.media_type || 'all');
  const [mediaTag, setMediaTag] = useState(mediaFilters.tag || '');
  const [mediaAuthor, setMediaAuthor] = useState(mediaFilters.author || '');
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [panelError, setPanelError] = useState('');
  const [exhausted, setExhausted] = useState(false);
  const sentinelRef = useRef(null);
  const items = mediaResults.items || [];
  const hasMore = !exhausted && Number(mediaResults.total || 0) > items.length;
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
  useEffect(() => {
    setMediaQuery(mediaFilters.q || '');
    setMediaType(mediaFilters.media_type || 'all');
    setMediaTag(mediaFilters.tag || '');
    setMediaAuthor(mediaFilters.author || '');
    setExhausted(false);
  }, [mediaFilters.q, mediaFilters.media_type, mediaFilters.tag, mediaFilters.author]);
  const activeFilters = [mediaType !== 'all' ? mediaType : '', mediaQuery, mediaTag, mediaAuthor].filter(Boolean);
  async function runMediaSearch(event) {
    event?.preventDefault();
    setExhausted(false);
    setPanelError('');
    setLoadingSearch(true);
    try {
      await loadMedia({ q: mediaQuery, media_type: mediaType, tag: mediaTag, author: mediaAuthor, limit: 64, offset: 0 });
    } catch (exc) {
      setPanelError(exc.message);
    } finally {
      setLoadingSearch(false);
    }
  }
  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const data = await loadMedia({ q: mediaQuery, media_type: mediaType, tag: mediaTag, author: mediaAuthor, append: true, limit: 64, offset: items.length });
      if (!data.items?.length || Number(data.added_count || 0) === 0) setExhausted(true);
    } catch (exc) {
      setPanelError(exc.message);
    } finally {
      setLoadingMore(false);
    }
  }
  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) loadMore();
    }, { rootMargin: '900px 0px' });
    const checkNearBottom = () => {
      const remaining = document.documentElement.scrollHeight - window.scrollY - window.innerHeight;
      if (remaining < 1200) loadMore();
    };
    observer.observe(node);
    window.addEventListener('scroll', checkNearBottom, { passive: true });
    window.addEventListener('resize', checkNearBottom);
    window.setTimeout(checkNearBottom, 250);
    const interval = window.setInterval(checkNearBottom, 1000);
    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', checkNearBottom);
      window.removeEventListener('resize', checkNearBottom);
      window.clearInterval(interval);
    };
  }, [items.length, hasMore, loadingMore, mediaQuery, mediaType, mediaTag, mediaAuthor]);
  return (
    <>
      <section className="panel">
        <div className="panelHead"><h2>{t.virtualLibrary}</h2><div className="panelActions"><MediaZoomControl value={mediaZoom} setValue={setMediaZoom} t={t} /><button className="panelButton" onClick={() => start('index-metadata')}><Database size={16} />{t.rebuildIndex}</button></div><span>{mediaResults.total || 0}</span></div>
        {Number(mediaResults.total || 0) === 0 && <div className="hintBox"><span>{t.noIndexHint}</span></div>}
        <form className="mediaSearchBar" onSubmit={runMediaSearch}>
          <select value={mediaType} onChange={event => { setMediaType(event.target.value); setExhausted(false); loadMedia({ q: mediaQuery, media_type: event.target.value, tag: mediaTag, author: mediaAuthor, limit: 64, offset: 0 }).catch(exc => setPanelError(exc.message)); }}>
            <option value="all">{t.allMedia}</option>
            <option value="photo">{t.photosOnly}</option>
            <option value="video">{t.videosOnly}</option>
          </select>
          <input value={mediaQuery} onChange={event => setMediaQuery(event.target.value)} placeholder={t.mediaSearch} />
          <input value={mediaTag} onChange={event => setMediaTag(event.target.value)} placeholder={t.tags} />
          <input value={mediaAuthor} onChange={event => setMediaAuthor(event.target.value)} placeholder={t.authorName} />
          <button type="submit" disabled={loadingSearch}><Search size={16} />{loadingSearch ? t.loadingMore : t.searchResults}</button>
        </form>
        {activeFilters.length > 0 && <div className="hintBox smallHint"><span>{t.activeFilters}: {activeFilters.join(' / ')}</span></div>}
        {panelError && <div className="alert compact">{panelError}</div>}
        <MediaGrid items={items} loadMedia={loadMedia} onDeleted={onDeleted} onPatched={onPatched} mediaZoom={mediaZoom} t={t} />
        <div className="infiniteSentinel" ref={sentinelRef}>{loadingMore ? t.loadingMore : hasMore ? t.scrollForMore : t.noMoreMedia}</div>
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
            <img src={`/api/media/${item.id}/thumbnail?v=${THUMBNAIL_REVISION}`} alt={item.filename} loading="lazy" decoding="async" onError={event => { event.currentTarget.style.display = 'none'; }} />
            <div><strong>{item.role}</strong><span>{item.filename}</span></div>
          </div>
        ))}
      </div>
    </article>
  );
}

function MediaGrid({ items, mediaZoom, onDeleted, onPatched, t }) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const requestRef = useRef(0);
  async function open(item) {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setSelected(item);
    setDetail(null);
    setDetailError('');
    setDetailLoading(true);
    try {
      const data = await api(`/api/media/${item.id}`);
      if (requestRef.current !== requestId) return;
      setDetail(data);
      onPatched?.(data);
    } catch (exc) {
      if (requestRef.current === requestId) setDetailError(exc.message);
    } finally {
      if (requestRef.current === requestId) setDetailLoading(false);
    }
  }
  async function reloadSelected(mediaId) {
    const data = await api(`/api/media/${mediaId}`);
    setDetail(data);
    setSelected(data);
    onPatched?.(data);
    return data;
  }
  if (!items?.length) return <Empty label={t.noRows} />;
  return (
    <>
      <div className="mediaGrid" style={{ '--media-card-width': `${Number(mediaZoom || 280)}px` }}>
        {items.map((item, index) => (
          <button className="mediaCard" key={item.id} data-media-id={item.id} aria-label={`${item.media_type || 'media'} ${item.filename || item.id}`} onClick={() => open(item)}>
            <MediaThumbImage item={item} priority={index < 8} />
            <div className="mediaMeta">
              <strong>{item.author || item.person || item.filename}</strong>
              <p>{item.filename}</p>
              {(item.semantic_score || item.match_reasons?.length) && (
                <div className="matchReasons">
                  {item.semantic_score && <span>{t.semanticScore || 'Semantic'} {Number(item.semantic_score).toFixed(2)}</span>}
                  {(item.match_reasons || []).slice(0, 3).map(reason => <span key={reason}>{reason}</span>)}
                </div>
              )}
              <div className="faceStats">
                <span>{item.media_type}</span>
                {item.quality && <span>{item.quality}</span>}
                {item.scene && <span>{item.scene}</span>}
              </div>
            </div>
          </button>
        ))}
      </div>
      {selected && <MediaViewer item={selected} detail={detail} loading={detailLoading} error={detailError} reload={reloadSelected} onDeleted={onDeleted} onPatched={onPatched} close={() => { requestRef.current += 1; setSelected(null); setDetail(null); setDetailError(''); }} t={t} />}
    </>
  );
}

function ModalPortal({ children }) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const previousPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`;
    return () => {
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPaddingRight;
    };
  }, []);
  return createPortal(children, document.body);
}

function MediaViewer({ item, detail, loading, error, reload, onDeleted, onPatched, close, t }) {
  const data = detail || item;
  const tags = Array.isArray(data.tags) ? data.tags : String(data.tags || '').split(',').filter(Boolean).map(tag => ({ tag }));
  const timeline = Array.isArray(data.timeline) ? data.timeline : [];
  const transcriptSegments = Array.isArray(data.transcript?.segments) ? data.transcript.segments : [];
  const timedTranscriptSegments = transcriptSegments.filter(segment => {
    const text = String(segment?.text || '').trim();
    const start = Number(segment?.start ?? segment?.start_seconds ?? 0);
    const end = Number(segment?.end ?? segment?.end_seconds ?? 0);
    return text && Number.isFinite(start) && Number.isFinite(end) && end > start && !(start === 0 && end <= 4 && text.length > 240);
  });
  const hasPlayableSubtitles = data.media_type === 'video' && timedTranscriptSegments.length > 0;
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [manualTag, setManualTag] = useState('');
  const [manualCategory, setManualCategory] = useState('');
  const [authorDraft, setAuthorDraft] = useState(data.author || '');
  const [busyAction, setBusyAction] = useState('');
  const [contactSheetMissing, setContactSheetMissing] = useState(false);
  const isFavorite = tags.some(tag => tag.tag === 'Favorite' && tag.state !== 'rejected');
  useEffect(() => setAuthorDraft(data.author || ''), [data.id, data.author]);
  useEffect(() => setContactSheetMissing(false), [data.id]);
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') close();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [close]);
  async function refreshDetail() {
    if (reload && data.id) await reload(data.id);
  }
  async function runViewerAction(name, action) {
    setBusyAction(name);
    try {
      await action();
    } catch (exc) {
      setFeedbackMessage(exc.message || String(exc));
    } finally {
      setBusyAction('');
    }
  }
  async function sendTagFeedback(tag, verdict) {
    if (!data.id || !tag?.tag) return;
    await runViewerAction('tag-feedback', async () => {
      await api(`/api/media/${data.id}/tag-feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag: tag.tag, category: tag.category || '', verdict }),
      });
      setFeedbackMessage(`${tag.tag}: ${t.tagFeedbackSaved}`);
      await refreshDetail();
    });
  }
  async function toggleFavorite() {
    if (!data.id) return;
    await runViewerAction('favorite', async () => {
      await api(`/api/media/${data.id}/favorite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ favorite: !isFavorite }),
      });
      setFeedbackMessage(t.favoriteSaved);
      await refreshDetail();
    });
  }
  async function saveManualTag(event) {
    event.preventDefault();
    if (!manualTag.trim() || !data.id) return;
    await runViewerAction('manual-tag', async () => {
      await api(`/api/media/${data.id}/manual-tag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag: manualTag.trim(), category: manualCategory.trim() }),
      });
      setManualTag('');
      setManualCategory('');
      setFeedbackMessage(t.manualEditSaved);
      await refreshDetail();
    });
  }
  async function saveAuthor(event) {
    event.preventDefault();
    if (!data.id) return;
    await runViewerAction('author', async () => {
      await api(`/api/media/${data.id}/author`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author: authorDraft.trim() }),
      });
      setFeedbackMessage(t.manualEditSaved);
      await refreshDetail();
    });
  }
  async function deleteMedia() {
    if (!data.id || !window.confirm(t.deleteMediaConfirm)) return;
    await runViewerAction('delete', async () => {
      await api(`/api/media/${data.id}`, { method: 'DELETE' });
      setFeedbackMessage(t.mediaDeleted);
      onDeleted?.(data.id);
      close();
    });
  }
  async function rebuildThumbnail() {
    if (!data.id) return;
    await runViewerAction('thumbnail', async () => {
      await api(`/api/media/${data.id}/thumbnail/rebuild`, { method: 'POST' });
      setFeedbackMessage(t.thumbnailRebuilt);
      await refreshDetail();
    });
  }
  async function rebuildVideoOverview() {
    if (!data.id || data.media_type !== 'video') return;
    await runViewerAction('contact-sheet', async () => {
      await api(`/api/media/${data.id}/contact-sheet/rebuild`, { method: 'POST' });
      setContactSheetMissing(false);
      setFeedbackMessage(t.videoOverviewRebuilt);
      await refreshDetail();
    });
  }
  return (
    <ModalPortal>
    <div className="viewerBackdrop" role="dialog" aria-modal="true">
      <div className="viewerPanel">
        <div className="viewerHead">
          <h2>{t.mediaDetail}</h2>
          <div className="viewerActions">
            <button className={`iconButton ${isFavorite ? 'isFavorite' : ''}`} onClick={toggleFavorite} disabled={!!busyAction || loading} title={isFavorite ? t.unfavorite : t.favorite} aria-label={isFavorite ? t.unfavorite : t.favorite}><Heart size={18} /></button>
            <button className="iconButton" onClick={rebuildThumbnail} disabled={!!busyAction || loading} title={t.rebuildThumbnail} aria-label={t.rebuildThumbnail}><RefreshCw size={18} /></button>
            {data.media_type === 'video' && <button className="iconButton" onClick={rebuildVideoOverview} disabled={!!busyAction || loading} title={t.rebuildVideoOverview} aria-label={t.rebuildVideoOverview}><Film size={18} /></button>}
            <button className="iconButton dangerIcon" onClick={deleteMedia} disabled={!!busyAction || loading} title={t.deleteMedia} aria-label={t.deleteMedia}><Trash2 size={18} /></button>
            <button className="iconButton" onClick={close} title={t.close} aria-label={t.close}><XCircle size={18} /></button>
          </div>
        </div>
        {loading && <div className="hintBox compact"><span>{t.loadingDetail}</span></div>}
        {error && <div className="alert compact">{t.loadFailed}: {error}</div>}
        <div className="viewerBody">
          <div className="viewerMedia">
            {data.media_type === 'video' ? (
              <video src={`/api/media/${data.id}/file`} controls poster={`/api/media/${data.id}/thumbnail?v=${THUMBNAIL_REVISION}`}>
                {hasPlayableSubtitles && <track kind="subtitles" srcLang={data.transcript?.language || 'und'} label={t.originalSubtitles} src={`/api/media/${data.id}/subtitles.vtt?mode=original`} default />}
                {hasPlayableSubtitles && <track kind="subtitles" srcLang="zh" label={t.bilingualSubtitles} src={`/api/media/${data.id}/subtitles.vtt?mode=bilingual`} />}
              </video>
            ) : <img src={`/api/media/${data.id}/file`} alt={data.filename} />}
          </div>
          <div className="viewerInfo">
            <form className="manualEditForm" onSubmit={saveAuthor}>
              <label>{t.authorName}<input value={authorDraft} onChange={event => setAuthorDraft(event.target.value)} placeholder={t.authorName} /></label>
              <button type="submit" disabled={busyAction === 'author'}><Save size={15} />{t.saveAuthor}</button>
            </form>
            <form className="manualEditForm tagEditForm" onSubmit={saveManualTag}>
              <label>{t.manualTag}<input value={manualTag} onChange={event => setManualTag(event.target.value)} placeholder={t.tags} /></label>
              <label>{t.tagCategory}<input value={manualCategory} onChange={event => setManualCategory(event.target.value)} placeholder="manual" /></label>
              <button type="submit" disabled={busyAction === 'manual-tag' || !manualTag.trim()}><Tags size={15} />{t.addTag}</button>
            </form>
            <div className="list">
              <div className="row"><span>{t.authorName}</span><strong>{data.author || '-'}</strong></div>
              <div className="row"><span>{t.originalName}</span><strong>{data.display_original_name || data.original_name || data.filename}</strong></div>
              <div className="row"><span>{t.indexedName}</span><strong>{data.filename}</strong></div>
              <div className="row"><span>{t.sourceOriginalPath}</span><strong>{data.source_original_path || '-'}</strong></div>
              <div className="row"><span>{t.filePath}</span><strong>{data.relative_path || data.filename}</strong></div>
              <div className="row"><span>{t.thumbnail}</span><strong>{data.resolution || data.quality || '-'}</strong></div>
              <div className="row"><span>{t.media}</span><strong>{data.media_type}</strong></div>
            </div>
            {data.media_type === 'video' && data.contact_sheet && !contactSheetMissing && (
              <section className="videoOverview">
                <h3>{t.videoOverview}</h3>
                <img src={`/api/media/${data.id}/contact-sheet`} alt={t.videoOverview} loading="lazy" onError={() => setContactSheetMissing(true)} />
              </section>
            )}
            {data.media_type === 'video' && (!data.contact_sheet || contactSheetMissing) && (
              <div className="hintBox compact videoOverviewAction">
                <span>{t.videoOverviewMissing}</span>
                <button onClick={rebuildVideoOverview} disabled={!!busyAction}><Film size={15} />{t.rebuildVideoOverview}</button>
              </div>
            )}
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
            {hasPlayableSubtitles && <div className="hintBox smallHint"><span>{t.subtitles}</span><a href={`/api/media/${data.id}/subtitles.vtt?mode=original`} target="_blank" rel="noreferrer">WebVTT</a></div>}
            {data.media_type === 'video' && data.transcript?.text && !hasPlayableSubtitles && <div className="hintBox smallHint"><span>{t.textTranscriptOnly}</span></div>}
            {timedTranscriptSegments.length > 0 ? (
              <div className="transcriptSegments">
                <h4>{t.transcriptSegments}</h4>
                {timedTranscriptSegments.slice(0, 200).map((segment, index) => {
                  const start = Number(segment.start ?? segment.start_seconds ?? 0);
                  const end = Number(segment.end ?? segment.end_seconds ?? 0);
                  return <div className="transcriptSegment" key={`${start}-${end}-${index}`}><span>{formatSeconds(start)} - {formatSeconds(end)}</span><p>{segment.text}</p></div>;
                })}
              </div>
            ) : data.transcript?.text ? <pre className="transcriptBlock">{data.transcript.text}</pre> : <div className="empty smallEmpty">{t.noTranscript}</div>}
          </div>
        </div>
      </div>
    </div>
    </ModalPortal>
  );
}

function formatSeconds(value) {
  const seconds = Math.max(0, Math.floor(Number(value || 0)));
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${minutes}:${String(remain).padStart(2, '0')}`;
}

function mediaResolutionLabel(item) {
  const raw = String(item?.resolution || item?.quality || '').trim();
  if (!raw || raw.toLowerCase() === 'na' || raw.toLowerCase() === 'resna') return '';
  const normalized = raw.replace(/[×X]/g, 'x');
  const match = normalized.match(/(\d{3,5})x(\d{3,5})/);
  if (match) {
    const width = Number(match[1]);
    const height = Number(match[2]);
    if (width >= 3800 || height >= 2100) return '4K';
    if (height >= 1400) return `${Math.round(height / 10) * 10}p`;
    return `${height}p`;
  }
  if (/4k/i.test(raw)) return '4K';
  const pMatch = raw.match(/\b(2160|1440|1080|720|480)p\b/i);
  if (pMatch) return `${pMatch[1]}p`;
  return raw.length > 12 ? `${raw.slice(0, 11)}…` : raw;
}

function AuthorsPanel({ authors, renameAuthor, excludeAuthor, syncAuthors, onDeleted, onPatched, mediaZoom, t }) {
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState('files');
  const [scope, setScope] = useState('all');
  const [view, setView] = useState('cards');
  const [selected, setSelected] = useState(null);
  const [media, setMedia] = useState({ items: [], total: 0 });
  const [collectionLoading, setCollectionLoading] = useState(false);
  const [collectionError, setCollectionError] = useState('');
  async function openAuthor(author) {
    setSelected(author);
    setMedia({ items: [], total: 0 });
    setCollectionError('');
    setCollectionLoading(true);
    try {
      const data = await api(`/api/authors/${encodeURIComponent(author.name)}/media?limit=120`);
      setMedia(data);
    } catch (exc) {
      setCollectionError(exc.message);
    } finally {
      setCollectionLoading(false);
    }
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
        <AuthorTable authors={filtered} openAuthor={openAuthor} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />
      )}
      {selected && <CollectionViewer title={selected.name} subtitle={`${selected.files} ${t.media}`} loading={collectionLoading} error={collectionError} items={media.items || []} onDeleted={onDeleted} onPatched={onPatched} mediaZoom={mediaZoom} close={() => setSelected(null)} t={t} />}
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

function AuthorTable({ authors, openAuthor, renameAuthor, excludeAuthor, t }) {
  if (!authors.length) return <section className="panel"><Empty label={t.noRows} /></section>;
  return (
    <section className="panel">
      <div className="tableWrap authorTable">
        <table>
          <thead><tr><th>{t.thumbnail}</th><th>{t.authorName}</th><th>{t.files}</th><th>{t.photos}</th><th>{t.videos}</th><th>FaceGroups</th><th>{t.showMedia}</th><th>{t.renameTo}</th><th>{t.excludeAuthor}</th></tr></thead>
          <tbody>{authors.map(author => <AuthorTableRow author={author} key={author.name} openAuthor={openAuthor} renameAuthor={renameAuthor} excludeAuthor={excludeAuthor} t={t} />)}</tbody>
        </table>
      </div>
    </section>
  );
}

function AuthorTableRow({ author, openAuthor, renameAuthor, excludeAuthor, t }) {
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
      <td><button className="panelButton miniButton" onClick={() => openAuthor(author)}><ImageIcon size={14} />{t.showMedia}</button></td>
      <td><form className="inlineForm" onSubmit={event => { event.preventDefault(); renameAuthor(author.name, target); }}><input value={target} onChange={event => setTarget(event.target.value)} /><button type="submit" title={t.renameTo}><Save size={14} /></button></form></td>
      <td><button className="dangerButton" onClick={() => excludeAuthor(author.name)}><Archive size={14} />{t.excludeAuthor}</button></td>
    </tr>
  );
}

function FaceGroupsPanel({ faces, suggestions, nameFace, mergeFace, mergeNamedFaces, onDeleted, onPatched, mediaZoom, t }) {
  const [selected, setSelected] = useState(null);
  const [media, setMedia] = useState({ items: [], total: 0 });
  const [collectionLoading, setCollectionLoading] = useState(false);
  const [collectionError, setCollectionError] = useState('');
  async function openFace(face) {
    setSelected(face);
    setMedia({ items: [], total: 0 });
    setCollectionError('');
    setCollectionLoading(true);
    try {
      const data = await api(`/api/face-groups/${encodeURIComponent(face.face_group)}/media?limit=160`);
      setMedia(data);
    } catch (exc) {
      setCollectionError(exc.message);
    } finally {
      setCollectionLoading(false);
    }
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
      {selected && <CollectionViewer title={selected.actor_name || selected.face_group} subtitle={selected.face_group} loading={collectionLoading} error={collectionError} items={media.items || []} onDeleted={onDeleted} onPatched={onPatched} mediaZoom={mediaZoom} close={() => setSelected(null)} t={t} />}
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

function CollectionViewer({ title, subtitle, items, loading, error, onDeleted, onPatched, mediaZoom, close, t }) {
  return (
    <ModalPortal>
    <div className="viewerBackdrop" role="dialog" aria-modal="true">
      <div className="viewerPanel collectionPanel">
        <div className="viewerHead"><div><h2>{title}</h2><p>{subtitle}</p></div><button className="iconButton" onClick={close}><XCircle size={18} /></button></div>
        <div className="collectionBody">
          {loading && <div className="hintBox compact"><span>{t.loadingMore}</span></div>}
          {error && <div className="alert compact">{t.loadFailed}: {error}</div>}
          {!loading && <MediaGrid items={items} onDeleted={onDeleted} onPatched={onPatched} mediaZoom={mediaZoom} t={t} />}
        </div>
      </div>
    </div>
    </ModalPortal>
  );
}

function LogsPanel({ jobs, applied, openJob, setActive, t }) {
  const [filter, setFilter] = useState('all');
  const sorted = sortJobsNewest(jobs);
  const filters = ['all', 'running', 'warning', 'error', 'completed'];
  const counts = filters.reduce((acc, key) => {
    acc[key] = key === 'all' ? sorted.length : sorted.filter(job => jobKind(job) === key).length;
    return acc;
  }, {});
  const visible = filter === 'all' ? sorted : sorted.filter(job => jobKind(job) === filter);
  return <section className="panel"><div className="panelHead"><h2>{t.recentLogs}</h2><span>{t.latestFirst} · {applied.rows} {t.moveLogRows}</span></div>
    <div className="statusTabs" role="tablist" aria-label={t.recentLogs}>
      {filters.map(key => <button key={key} className={filter === key ? 'active' : ''} onClick={() => setFilter(key)}>{jobKindLabel(key, t)}<span>{counts[key] || 0}</span></button>)}
    </div>
    <div className="jobs">{visible.map(job => {
    const kind = jobKind(job);
    const stamp = formatDateTime(job.finished_at || job.heartbeat_at || job.started_at || job.created_at);
    return <button className={`job logJob ${kind}`} key={job.id} onClick={() => { openJob(job.id); setActive('jobs'); }}><div className="jobMain"><strong>#{job.id} {t.commandNames?.[job.command] || job.command}</strong><p>{jobDiagnostic(job, t)}</p><small>{stamp}</small></div><JobBadge status={job.status} kind={kind} label={jobKindLabel(kind, t)} /></button>;
  })}</div></section>;
}

function FieldLabel({ label, help }) {
  return (
    <span className="fieldLabel">
      {label}
      {help && <HelpCircle className="fieldHelp" size={15} tabIndex="0" aria-label={help}><title>{help}</title></HelpCircle>}
    </span>
  );
}

function CapabilityCenter({ catalog, start, busy, t }) {
  const models = catalog?.models || [];
  const byId = Object.fromEntries(models.map(model => [model.id, model]));
  const ready = id => byId[id]?.status === 'ready';
  const capabilityRows = [
    { id: 'filename', group: 'core', name: t.filename_analysis, status: 'ready', source: t.builtIn, purpose: t.sourceDirsHint, deleteable: false, action: 'analyze-filenames' },
    { id: 'thumbs', group: 'core', name: t.frameCache, status: 'ready', source: t.builtIn, purpose: t.thumbnailHealthHint, deleteable: false, action: 'repair-thumbnails' },
    { id: 'metadata', group: 'core', name: t.metadataBackfill, status: 'ready', source: 'ffprobe / Pillow', purpose: t.metadataBackfillHint, deleteable: false, action: 'metadata-backfill' },
    { id: 'faces', group: 'downloadable', name: t.faces, status: ready('insightface-buffalo-l') ? 'ready' : 'missing', source: 'InsightFace / ArcFace', purpose: t.faceMergeHelp, model: byId['insightface-buffalo-l'], deleteable: true, action: 'workflow-face-balanced' },
    { id: 'vision', group: 'downloadable', name: t.visionPipeline, status: ready('openclip-vit-l') ? 'ready' : 'missing', source: 'OpenCLIP / CLIP', purpose: t.modelHint, model: byId['openclip-vit-l'], deleteable: true, action: 'index-semantic-vision' },
    { id: 'speech', group: 'downloadable', name: t.transcriptWorkflow, status: ready('sensevoice-small-gguf') || ready('funasr-nano-onnx') || ready('faster-whisper-small') ? 'ready' : 'missing', source: 'SenseVoice / Fun-ASR / Whisper', purpose: t.transcribeWorkflowHint, deleteable: true, action: 'transcribe' },
    { id: 'subtitle', group: 'downloadable', name: t.subtitles, status: ready('funasr-nano-onnx') || ready('sensevoice-small-gguf') ? 'ready' : 'missing', source: 'WebVTT generator', purpose: t.textTranscriptOnly, deleteable: false, action: 'index-semantic-text' },
    { id: 'vectors', group: 'downloadable', name: t.diagnosticsTitle, status: ready('bge-small-text') && ready('openclip-vit-l') ? 'ready' : ready('openclip-vit-l') ? 'partial' : 'missing', source: 'BGE + OpenCLIP', purpose: t.quickFindHint, model: byId['bge-small-text'], deleteable: true, action: 'index-semantic-all' },
    { id: 'vlm', group: 'downloadable', name: 'VLM', status: ready('vlm-lite') ? 'ready' : 'missing', source: 'Local VLM', purpose: t.modelHint, model: byId['vlm-lite'], deleteable: true, action: 'diagnose-search' },
  ];
  const label = status => ({ ready: t.capabilityReady, partial: t.capabilityPartial, missing: t.capabilityMissing }[status] || status);
  const renderGroup = (group, title) => (
    <div className="capabilityGroup">
      <h3>{title}</h3>
      <div className="capabilityGrid">
        {capabilityRows.filter(item => item.group === group).map(item => (
          <article className={`capabilityCard ${item.status}`} key={item.id}>
            <div className="capabilityTop"><strong>{item.name}</strong><span>{label(item.status)}</span></div>
            <p><b>{t.purpose}</b> {item.purpose}</p>
            <p><b>{t.source}</b> {item.source}</p>
            <p><b>{t.modelSize}</b> {item.model ? prettyBytes(item.model.bytes) : t.builtIn} · {item.deleteable ? t.deleteable : t.notDeleteable}</p>
            {item.action && <button type="button" className="panelButton capabilityAction" disabled={busy} onClick={() => start(item.action)}>{t.runAction}: {t.commandNames?.[item.action] || item.action}</button>}
          </article>
        ))}
      </div>
    </div>
  );
  return (
    <section className="capabilityCenter">
      <div className="panelHead"><h2>{t.capabilityCenter}</h2><span>{catalog?.root || '/models'}</span></div>
      {renderGroup('core', t.coreCapabilities)}
      {renderGroup('downloadable', t.downloadableCapabilities)}
    </section>
  );
}

function ModelsPanel({ catalog, drafts, setDrafts, manifestDraft, setManifestDraft, modelDraftDirtyRef, manifestDraftDirtyRef, saveModelSource, saveManifestSource, pullModel, deleteModel, start, busy, t }) {
  const models = catalog?.models || [];
  const statusLabel = {
    ready: t.modelReady,
    missing: t.modelMissing,
    needs_url: t.modelNeedsUrl,
  };
  const recommended = models.filter(model => model.recommended && model.status !== 'ready').length;
  function updateDraft(modelId, key, value) {
    modelDraftDirtyRef.current = true;
    setDrafts(current => ({ ...current, [modelId]: { ...(current[modelId] || {}), [key]: value } }));
  }
  function updateManifestDraft(value) {
    manifestDraftDirtyRef.current = true;
    setManifestDraft(value);
  }
  function modelPlaceholder(model) {
    if (model.id?.includes('onnx') || model.path?.endsWith('.onnx')) return 'https://github.com/.../model.onnx';
    if (model.path?.endsWith('.gguf')) return 'https://github.com/.../model.gguf';
    return 'https://github.com/.../model.bin';
  }
  function modelUrlSourceLabel(model) {
    if (model.url_source === 'default') return t.modelUrlSourceDefault;
    if (model.url_source === 'settings') return t.modelUrlSourceSettings;
    if (model.url_source === 'env') return t.modelUrlSourceEnv;
    return t.modelUrlSourceMissing;
  }
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
      <div className="modelManifestBox">
        <label>{t.modelManifestUrl}<input value={manifestDraft || ''} onChange={event => updateManifestDraft(event.target.value)} placeholder="https://github.com/.../tgmm-model-pack.json" /></label>
        <button className="panelButton" onClick={() => saveManifestSource(manifestDraft)}><Save size={16} />{t.saveModelSource}</button>
        <small>{t.modelManifestHint}</small>
      </div>
      <CapabilityCenter catalog={catalog} start={start} busy={busy} t={t} />
      {busy && <div className="hintBox smallHint"><span>{t.modelBusyHint}</span></div>}
      <div className="modelGrid">
        {models.map(model => {
          const draft = drafts?.[model.id] || { url: model.source_url || '', sha256: model.sha256 || '' };
          const description = t.locale === 'zh-CN' ? (model.description_zh || model.description) : model.description;
          return (
          <article className={`modelCard ${model.status}`} key={model.id}>
            <div className="modelCardTop">
              <HardDrive size={20} />
              <div>
                <strong>{model.name}</strong>
                <span>{model.category} · {model.kind === 'file' ? t.modelFile : t.modelRuntimeCache}</span>
              </div>
              <b>{statusLabel[model.status] || model.status}</b>
            </div>
            <p>{description}</p>
            <div className="modelMeta">
              <div><span>{t.modelSize}</span><strong>{prettyBytes(model.bytes)}</strong>{model.size_note && <small>{model.size_note}</small>}</div>
              <div><span>{t.modelPath}</span><strong title={model.path}>{model.path}</strong></div>
              {model.url_env && <div><span>URL env</span><strong>{model.url_env}{model.url_configured ? '' : ' unset'}</strong></div>}
              {model.official_url && <div><span>{t.modelOfficialRef}</span><a href={model.official_url} target="_blank" rel="noreferrer">{model.official_url}</a></div>}
            </div>
            {model.source_editable && (
              <div className="modelSourceForm">
                <label>{t.modelSourceUrl}<input value={draft.url || ''} onChange={event => updateDraft(model.id, 'url', event.target.value)} placeholder={modelPlaceholder(model)} /><small>{modelUrlSourceLabel(model)}</small></label>
                <label>{t.modelSha256}<input value={draft.sha256 || ''} onChange={event => updateDraft(model.id, 'sha256', event.target.value)} placeholder="optional 64-char checksum" /></label>
                <button className="panelButton" onClick={() => saveModelSource(model.id, draft)}><Save size={16} />{t.saveModelSource}</button>
              </div>
            )}
            <div className="modelActions">
              <button className="panelButton" disabled={busy || model.status === 'needs_url'} onClick={() => pullModel(model.id)}><Download size={16} />{t.downloadModel}</button>
              <button className="panelButton dangerButton" disabled={!model.present || busy} onClick={() => deleteModel(model.id)}><Trash2 size={16} />{t.deleteModel}</button>
            </div>
          </article>
        );
        })}
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
    transcript_engine: 'auto',
    audio_tag_mode: 'sensevoice-sample',
    audio_tag_sample_seconds: 30,
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
          <label><FieldLabel label={t.computeDevice} help={t.settingHelp?.computeDevice} /><select value={cfg.compute_device || 'auto'} onChange={event => update('compute_device', event.target.value)}><option value="auto">{t.auto}</option><option value="gpu">{t.gpuPreferred}</option><option value="cpu">{t.cpuOnly}</option></select><small>{t.gpuHint}</small></label>
          <label><FieldLabel label={t.ffmpegHwaccel} help={t.settingHelp?.ffmpegHwaccel} /><select value={cfg.ffmpeg_hwaccel || 'auto'} onChange={event => update('ffmpeg_hwaccel', event.target.value)}><option value="auto">{t.auto}</option><option value="vaapi">VAAPI</option><option value="qsv">Intel QSV</option><option value="none">{t.ffmpegNone}</option></select></label>
          <label><FieldLabel label="Frame workers" help={t.settingHelp?.frameWorkers} /><input type="number" min="1" max="16" value={cfg.frame_workers || 1} onChange={event => update('frame_workers', event.target.value)} /><small>NAS 建议 3-4；太高会打满磁盘 IO。</small></label>
          <label><FieldLabel label="Frames per video" help={t.settingHelp?.framesPerVideo} /><input type="number" min="1" max="12" value={cfg.frames_per_video || 3} onChange={event => update('frames_per_video', event.target.value)} /></label>
          <label><FieldLabel label="Checkpoint every" help={t.settingHelp?.checkpointEvery} /><input type="number" min="10" max="1000" value={cfg.frame_checkpoint_every || 100} onChange={event => update('frame_checkpoint_every', event.target.value)} /><small>抽帧索引和任务进度的落盘频率。</small></label>
          <label><FieldLabel label={t.openvinoDevice} help={t.settingHelp?.openvinoDevice} /><select value={cfg.openvino_device || 'GPU'} onChange={event => update('openvino_device', event.target.value)}><option value="GPU">{t.gpu}</option><option value="CPU">{t.cpu}</option><option value="AUTO">{t.openvinoAuto}</option></select></label>
          <label><FieldLabel label={t.openclipModel} help={t.settingHelp?.openclipModel} /><input value={cfg.openclip_model || 'ViT-L-14'} onChange={event => update('openclip_model', event.target.value)} placeholder="ViT-L-14" /><small>{t.openclipHint}</small></label>
          <label><FieldLabel label={t.openclipPretrained} help={t.settingHelp?.openclipPretrained} /><input value={cfg.openclip_pretrained || 'laion2b_s32b_b82k'} onChange={event => update('openclip_pretrained', event.target.value)} placeholder="laion2b_s32b_b82k" /></label>
          <label><FieldLabel label={t.openclipStrongModel} help={t.settingHelp?.openclipModel} /><input value={cfg.openclip_strong_model || 'ViT-H-14'} onChange={event => update('openclip_strong_model', event.target.value)} placeholder="ViT-H-14" /></label>
          <label><FieldLabel label={t.openclipStrongPretrained} help={t.settingHelp?.openclipPretrained} /><input value={cfg.openclip_strong_pretrained || 'laion2b_s32b_b79k'} onChange={event => update('openclip_strong_pretrained', event.target.value)} placeholder="laion2b_s32b_b79k" /></label>
          <label><FieldLabel label={t.openclipStrongThreshold} help={t.settingHelp?.openclipStrongThreshold} /><input type="number" min="0.01" max="0.99" step="0.01" value={cfg.openclip_strong_threshold ?? 0.62} onChange={event => update('openclip_strong_threshold', event.target.value)} /></label>
          <label className="checkLine"><input type="checkbox" checked={cfg.openclip_strong_low_conf_only !== false} onChange={event => update('openclip_strong_low_conf_only', event.target.checked)} />{t.openclipStrongLowOnly}</label>
          <label><FieldLabel label={t.faceProviders} help={t.settingHelp?.faceProviders} /><select value={cfg.face_providers || 'OpenVINOExecutionProvider,CPUExecutionProvider'} onChange={event => update('face_providers', event.target.value)}><option value="OpenVINOExecutionProvider,CPUExecutionProvider">OpenVINO + CPU fallback</option><option value="CPUExecutionProvider">CPUExecutionProvider</option></select></label>
          <label><FieldLabel label={t.transcriptEngine} help={t.settingHelp?.transcriptEngine} /><select value={cfg.transcript_engine || cfg.asr_engine || 'auto'} onChange={event => update('transcript_engine', event.target.value)}><option value="auto">{t.transcriptAuto}</option><option value="funasr-nano-onnx">{t.asrFunAsrNano}</option><option value="sensevoice-gguf">{t.asrSenseVoice}</option><option value="faster-whisper">{t.asrWhisper}</option></select></label>
          <label><FieldLabel label={t.audioTagMode} help={t.settingHelp?.audioTagMode} /><select value={cfg.audio_tag_mode || 'sensevoice-sample'} onChange={event => update('audio_tag_mode', event.target.value)}><option value="sensevoice-sample">{t.audioTagSenseVoiceSample}</option><option value="sensevoice-full">{t.audioTagSenseVoiceFull}</option><option value="off">{t.audioTagOff}</option></select></label>
          <label><FieldLabel label={t.audioTagSampleSeconds} help={t.settingHelp?.audioTagSampleSeconds} /><input type="number" min="0" max="3600" value={cfg.audio_tag_sample_seconds ?? 30} onChange={event => update('audio_tag_sample_seconds', event.target.value)} /></label>
          <label><FieldLabel label={t.asrEngine} help={t.settingHelp?.asrEngine} /><select value={cfg.asr_engine || 'auto'} onChange={event => update('asr_engine', event.target.value)}><option value="auto">{t.asrAuto}</option><option value="sensevoice-gguf">{t.asrSenseVoice}</option><option value="faster-whisper">{t.asrWhisper}</option></select></label>
          <label>{t.senseVoiceModel}<input value={cfg.sensevoice_gguf_model || '/models/sensevoice/SenseVoiceSmall.gguf'} onChange={event => update('sensevoice_gguf_model', event.target.value)} /></label>
          <label>{t.senseVoiceBin}<input value={cfg.sensevoice_gguf_bin || 'llama-sensevoice'} onChange={event => update('sensevoice_gguf_bin', event.target.value)} /></label>
          <label>{t.senseVoiceCommand}<input value={cfg.sensevoice_gguf_command || ''} onChange={event => update('sensevoice_gguf_command', event.target.value)} placeholder="{bin} -m {model} -f {audio} --language auto" /><small>{t.senseVoiceCommandHint}</small></label>
          <label><FieldLabel label={t.whisperDevice} help={t.settingHelp?.whisperDevice} /><select value={cfg.whisper_device || 'cpu'} onChange={event => update('whisper_device', event.target.value)}><option value="cpu">{t.cpu}</option><option value="cuda">CUDA</option></select></label>
          <label><FieldLabel label={t.transcribeMaxSeconds} help={t.settingHelp?.transcribeMaxSeconds} /><input type="number" min="0" max="86400" value={cfg.transcribe_max_seconds ?? 0} onChange={event => update('transcribe_max_seconds', event.target.value)} /><small>{t.transcribeFullHint}</small></label>
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
