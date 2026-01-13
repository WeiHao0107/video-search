<script setup>
import { ref, reactive, nextTick } from 'vue';
import axios from 'axios';
import { Search, Play, Clock, FileVideo, ChevronRight } from 'lucide-vue-next';

const query = ref('');
const results = ref([]);
const loading = ref(false);
const videoPlayer = ref(null); // 綁定 video DOM

const activeVideo = reactive({
  filename: null,
  url: null,
  currentTime: 0,
  text: ''
});

// 格式化時間
const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
};

const handleSearch = async () => {
  if (!query.value.trim()) return;
  
  loading.value = true;
  results.value = [];
  activeVideo.filename = null; // 清空當前播放
  
  try {
    const response = await axios.post('/api/search', {
      query: query.value
    });
    results.value = response.data;
  } catch (error) {
    console.error("Search error:", error);
    alert("搜尋發生錯誤，請確認後端是否已啟動");
  } finally {
    loading.value = false;
  }
};

const playSegment = async (filename, videoUrl, time, text) => {
  // 1. 設定狀態
  activeVideo.filename = filename;
  activeVideo.text = text;
  
  // 判斷是否需要換影片來源 (避免同影片切換片段時重新載入)
  if (activeVideo.url !== videoUrl) {
    activeVideo.url = videoUrl;
  }
  
  // 2. 捲動到頂部
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // 3. 等待 DOM 更新後控制影片
  await nextTick();
  
  if (videoPlayer.value) {
    videoPlayer.value.currentTime = time;
    try {
      await videoPlayer.value.play();
    } catch (e) {
      console.warn("Autoplay blocked:", e);
    }
  }
};
</script>

<template>
  <div class="min-h-screen p-6 max-w-5xl mx-auto">
    
    <!-- 標題區 -->
    <header class="text-center mb-10 mt-6">
      <h1 class="text-4xl font-bold text-gray-800 mb-2 flex justify-center items-center gap-3">
        <FileVideo class="w-10 h-10 text-blue-600" />
        Video Semantic Search
      </h1>
      <p class="text-gray-500">輸入關鍵字，立刻找到影片中的對應片段</p>
    </header>

    <!-- 真實播放器 -->
    <div v-if="activeVideo.filename" class="mb-8 bg-black rounded-xl overflow-hidden shadow-2xl transition-all duration-500">
      <div class="aspect-video bg-black flex flex-col items-center justify-center relative">
        
        <video 
          ref="videoPlayer"
          :src="activeVideo.url"
          controls
          autoplay
          class="w-full h-full object-contain"
        >
          您的瀏覽器不支援 HTML5 影片標籤。
        </video>

        <!-- 字幕提示 (浮在影片上方，可選) -->
        <div v-if="activeVideo.text" class="absolute bottom-16 left-0 right-0 text-center px-10 pointer-events-none">
          <p class="bg-black/70 text-white px-4 py-2 inline-block rounded text-lg backdrop-blur-sm">
            {{ activeVideo.text }}
          </p>
        </div>
      </div>
      
      <!-- 播放資訊列 -->
      <div class="bg-gray-900 text-white px-6 py-3 flex justify-between items-center">
        <span class="font-medium text-gray-300">
          Playing: <span class="text-white">{{ activeVideo.filename }}</span>
        </span>
        <button @click="activeVideo.filename = null" class="text-sm text-gray-400 hover:text-white">
          Close Player
        </button>
      </div>
    </div>

    <!-- 搜尋列 -->
    <div class="relative mb-12 max-w-2xl mx-auto">
      <input 
        v-model="query"
        @keyup.enter="handleSearch"
        type="text" 
        placeholder="例如: neural network, vector database..." 
        class="w-full pl-12 pr-4 py-4 text-lg rounded-full border-2 border-gray-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 outline-none shadow-sm transition-all"
      />
      <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-6 h-6" />
      <button 
        @click="handleSearch"
        class="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white px-6 rounded-full font-medium transition-colors"
      >
        Search
      </button>
    </div>

    <!-- 讀取中 -->
    <div v-if="loading" class="text-center py-10">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-500">正在分析影片內容...</p>
    </div>

    <!-- 搜尋結果 -->
    <div v-else class="space-y-8">
      <div v-if="results.length === 0 && !loading && query" class="text-center text-gray-500 py-10">
        沒有找到相關內容，請嘗試其他關鍵字。
      </div>

      <div v-for="video in results" :key="video.video_id" class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
        <!-- 影片標題列 -->
        <div class="bg-gray-50 px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="bg-blue-100 p-2 rounded-lg">
              <FileVideo class="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 class="font-bold text-lg text-gray-800">{{ video.filename }}</h3>
              <p class="text-sm text-gray-500 flex items-center gap-2">
                Created: {{ new Date(video.created_at).toLocaleDateString() }}
              </p>
            </div>
          </div>
          <div class="text-sm text-blue-600 font-medium bg-blue-50 px-3 py-1 rounded-full">
            {{ video.children.length }} 個相關片段
          </div>
        </div>

        <!-- 命中片段列表 -->
        <div class="p-4">
          <div class="grid gap-3">
            <div 
              v-for="(child, idx) in video.children" 
              :key="idx"
              @click="playSegment(video.filename, video.video_url, child.start_seconds, child.text)"
              class="group flex items-start gap-4 p-3 rounded-xl hover:bg-blue-50 cursor-pointer transition-colors border border-transparent hover:border-blue-100"
            >
              <!-- 時間標記 -->
              <div class="flex-shrink-0 w-20 pt-1">
                <div class="flex items-center gap-1.5 text-blue-600 font-mono font-bold bg-blue-100/50 px-2 py-1 rounded group-hover:bg-blue-600 group-hover:text-white transition-colors text-sm justify-center">
                  <Play class="w-3 h-3 fill-current" />
                  {{ formatTime(child.start_seconds) }}
                </div>
              </div>

              <!-- 字幕內容 -->
              <div class="flex-grow">
                <p class="text-gray-700 leading-relaxed group-hover:text-gray-900">
                  {{ child.text }}
                </p>
                <!-- 相關度分數條 (視覺化) -->
                <div class="mt-2 h-1 w-24 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full bg-green-500" :style="{ width: `${child.score * 100}%` }"></div>
                </div>
              </div>

              <!-- Action Icon -->
              <div class="text-gray-300 group-hover:text-blue-500 pt-1">
                <ChevronRight class="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>