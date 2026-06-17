<template>
  <VeritasShell active="batch" :breadcrumbs="[{ label: 'Пакетная проверка' }]">
    <div style="padding:24px 28px;display:flex;flex-direction:column;gap:20px">
      <div>
        <h1 class="serif" style="font-size:28px;font-weight:400;letter-spacing:-0.01em;line-height:1.1">Пакетная проверка</h1>
        <p style="font-size:13px;color:var(--muted);margin-top:4px">Загрузите до 50 файлов — проверим параллельно, покажем сводку и подозрительные фрагменты.</p>
      </div>

      <div style="display:grid;grid-template-columns:1fr 360px;gap:16px;align-items:start">
        <!-- Drop zone + list -->
        <div class="va-card" style="padding:0;overflow:hidden;display:flex;flex-direction:column">
          <div style="padding:20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px"
            @dragover.prevent @drop.prevent="onDrop">
            <div style="width:44px;height:44px;border-radius:10px;background:var(--accent-bg);color:var(--accent-ink);display:grid;place-items:center">
              <VIcon name="upload" :size="20" />
            </div>
            <div style="flex:1">
              <div style="font-size:14px;font-weight:500">Перетащите файлы сюда</div>
              <div style="font-size:12px;color:var(--muted)">DOCX · PDF · TXT — до 50 файлов, 25 МБ каждый</div>
            </div>
            <label class="va-btn primary" style="cursor:pointer">
              Выбрать файлы
              <input type="file" accept=".docx,.pdf,.txt,.doc" multiple style="display:none" @change="onFilesChange" />
            </label>
          </div>

          <div style="padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between">
            <div style="font-size:13px;font-weight:500">В очереди · {{ files.length }}</div>
            <div style="display:flex;gap:8px">
              <button class="va-btn ghost" style="height:28px" @click="clearAll">Очистить</button>
              <button class="va-btn accent" style="height:28px" @click="runAll" :disabled="isRunning || files.length === 0">
                <VIcon name="zap" :size="12" /> {{ isRunning ? 'Проверяем…' : 'Запустить все' }}
              </button>
            </div>
          </div>

          <div>
            <div v-if="files.length === 0" style="padding:40px;text-align:center;color:var(--muted);font-size:13px">
              Нет файлов. Перетащите или выберите выше.
            </div>
            <div v-for="(f, i) in files" :key="i"
              class="batch-row"
              :class="{ 'batch-row--active': selectedIndex === i }"
              style="display:grid;grid-template-columns:1fr 96px 120px 110px 64px;align-items:center;gap:12px;padding:12px 16px;cursor:pointer"
              :style="{ borderBottom: i < files.length-1 ? '1px solid var(--border)' : 'none' }"
              @click="selectFile(i)">
              <div style="display:flex;align-items:center;gap:10px;min-width:0">
                <VIcon name="file" :size="14" style="color:var(--muted)" />
                <span style="font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ f.file.name }}</span>
              </div>
              <div style="font-size:12px;color:var(--muted)">
                <span v-if="f.result" class="tnum">{{ f.result.text_length?.toLocaleString('ru') }} слов</span>
                <span v-else>—</span>
              </div>
              <div>
                <template v-if="f.result">
                  <div style="display:flex;align-items:center;gap:8px">
                    <div style="width:30px;height:4px;background:var(--bg-sunken);border-radius:2px;overflow:hidden">
                      <div :style="{ width:`${aiPercentFromResult(f.result)}%`, height:'100%', background:'var(--ai)' }" />
                    </div>
                    <span class="tnum" style="font-size:12px">{{ Math.round(aiPercentFromResult(f.result)) }}%</span>
                  </div>
                </template>
                <template v-else-if="f.progress > 0">
                  <div style="display:flex;align-items:center;gap:8px">
                    <div style="flex:1;height:4px;background:var(--bg-sunken);border-radius:2px;overflow:hidden">
                      <div :style="{ width:`${f.progress}%`, height:'100%', background:'var(--accent)' }" />
                    </div>
                    <span class="tnum" style="font-size:11px;color:var(--muted)">{{ f.progress }}%</span>
                  </div>
                </template>
                <span v-else style="font-size:12px;color:var(--muted-2)">В очереди</span>
              </div>
              <div>
                <span v-if="f.error" class="va-chip ai" :title="f.error">Ошибка</span>
                <span v-else-if="f.result" :class="`va-chip ${verdictFromResult(f.result)}`">
                  {{ verdictLabelFromResult(f.result) }}
                </span>
                <span v-else-if="f.progress > 0" class="va-chip accent">Обработка</span>
                <span v-else class="va-chip">Ожидание</span>
              </div>
              <div style="display:flex;gap:4px;justify-content:flex-end">
                <button class="va-btn ghost" style="width:28px;height:28px;padding:0;justify-content:center"
                  title="Повторить проверку" :disabled="f.progress > 0 && f.progress < 100"
                  @click.stop="runOne(i)">
                  <VIcon name="refresh" :size="13" />
                </button>
                <button class="va-btn ghost" style="width:28px;height:28px;padding:0;justify-content:center"
                  title="Удалить" @click.stop="removeFile(i)">
                  <VIcon name="x" :size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Right column: detail / progress / summary -->
        <div style="display:flex;flex-direction:column;gap:12px">
          <!-- Selected file detail -->
          <div v-if="selected && selected.result" class="va-card" style="padding:18px;display:flex;flex-direction:column;gap:14px">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">
              <div style="min-width:0">
                <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600">Документ</div>
                <div style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" :title="selected.file.name">
                  {{ selected.file.name }}
                </div>
              </div>
              <VerdictBadge :verdict="verdictFromResult(selected.result)" />
            </div>

            <div style="display:flex;align-items:baseline;gap:8px">
              <span class="serif tnum" style="font-size:40px;font-weight:400;line-height:1">{{ Math.round(aiPercentFromResult(selected.result)) }}</span>
              <span style="font-size:16px;color:var(--muted)">% вероятность ИИ</span>
            </div>

            <div>
              <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:8px">
                Подозрительные фрагменты
              </div>
              <AiFragmentsList :windows="selected.result.pangram_response?.windows" :limit="20" />
            </div>

            <div style="display:flex;gap:8px">
              <button class="va-btn ghost" style="flex:1;height:34px;justify-content:center" @click="rerunSelected">
                <VIcon name="refresh" :size="13" /> Повторить
              </button>
              <button class="va-btn accent" style="flex:1;height:34px;justify-content:center" @click="openDetail(selected.result)">
                Полный разбор <VIcon name="external" :size="12" />
              </button>
            </div>
          </div>

          <div v-else-if="selected" class="va-card" style="padding:18px;font-size:13px;color:var(--muted)">
            Файл «{{ selected.file.name }}» ещё не проверен. Нажмите «Запустить все» или
            <VIcon name="refresh" :size="12" /> в строке файла.
          </div>

          <div class="va-card" style="padding:18px">
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:10px">Прогресс пакета</div>
            <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:12px">
              <span class="serif tnum" style="font-size:38px;font-weight:400;line-height:1">{{ doneCount }}</span>
              <span style="font-size:16px;color:var(--muted)">/ {{ files.length }} готово</span>
            </div>
            <div style="height:6px;background:var(--bg-sunken);border-radius:999px;overflow:hidden">
              <div :style="{ width: files.length ? `${(doneCount/files.length)*100}%` : '0%', height:'100%', background:'var(--accent)' }" />
            </div>
          </div>

          <div class="va-card" style="padding:18px">
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:12px">Сводка</div>
            <div v-for="(r, i) in summary" :key="r.label" style="display:flex;align-items:center;gap:10px;padding:8px 0" :style="{ borderBottom: i<2 ? '1px solid var(--border)' : 'none' }">
              <span class="va-dot" :style="{ background: r.color, width:'8px', height:'8px' }" />
              <span style="flex:1;font-size:13px">{{ r.label }}</span>
              <span class="tnum" style="font-size:13px;font-weight:600">{{ r.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </VeritasShell>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import VeritasShell from '../components/VeritasShell.vue'
import VIcon from '../components/VIcon.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import AiFragmentsList from '../components/workspace/AiFragmentsList.vue'
import { aiDetectionAPI } from '../services/api'
import type { AnalyzeResponse } from '../types/api'
import { resolveAiPercent, resolveVerdict, type Verdict } from '../utils/aiResult'

interface BatchFile { file: File; progress: number; result: AnalyzeResponse | null; error: string }

const router = useRouter()

const files = ref<BatchFile[]>([])
const isRunning = ref(false)
const selectedIndex = ref<number | null>(null)

const selected = computed(() => (selectedIndex.value === null ? null : files.value[selectedIndex.value] ?? null))
const doneCount = computed(() => files.value.filter((f) => f.result).length)

const summary = computed(() => {
  const done = files.value.filter((f) => f.result)
  return [
    { label: 'Человек', color: 'var(--human)', count: done.filter((f) => verdictFromResult(f.result) === 'human').length },
    { label: 'Смешанные', color: 'var(--mixed)', count: done.filter((f) => verdictFromResult(f.result) === 'mixed').length },
    { label: 'ИИ', color: 'var(--ai)', count: done.filter((f) => verdictFromResult(f.result) === 'ai').length },
  ]
})

const verdictFromResult = (result: AnalyzeResponse | null): Verdict => resolveVerdict(result?.pangram_response)
const aiPercentFromResult = (result: AnalyzeResponse | null) => resolveAiPercent(result?.pangram_response)

const verdictLabelFromResult = (result: AnalyzeResponse | null) => {
  const verdict = verdictFromResult(result)
  if (verdict === 'ai') return 'ИИ'
  if (verdict === 'human') return 'Человек'
  return 'Смешанные'
}

const addFiles = (newFiles: FileList | File[]) => {
  for (const f of Array.from(newFiles)) {
    if (files.value.length < 50) {
      files.value.push({ file: f, progress: 0, result: null, error: '' })
    }
  }
}

const onFilesChange = (e: Event) => {
  const fs = (e.target as HTMLInputElement).files
  if (fs) addFiles(fs)
}
const onDrop = (e: DragEvent) => {
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files)
}

const selectFile = (i: number) => {
  selectedIndex.value = i
}

const removeFile = (i: number) => {
  files.value.splice(i, 1)
  if (selectedIndex.value === i) {
    selectedIndex.value = null
  } else if (selectedIndex.value !== null && i < selectedIndex.value) {
    selectedIndex.value -= 1
  }
}

const clearAll = () => {
  files.value = []
  selectedIndex.value = null
}

const runOne = async (i: number) => {
  const f = files.value[i]
  if (!f) return
  f.error = ''
  f.result = null
  f.progress = 10
  try {
    f.progress = 50
    // detailed=true — нужно, чтобы получить посегментные ИИ-фрагменты
    f.result = await aiDetectionAPI.uploadFile(f.file, true)
    f.progress = 100
  } catch (e) {
    const apiError = e as { error?: string } | null
    f.error = apiError?.error || 'Ошибка'
    f.progress = 0
  }
}

const runAll = async () => {
  isRunning.value = true
  const pending = files.value
    .map((f, i) => ({ f, i }))
    .filter(({ f }) => !f.result)
  await Promise.all(pending.map(({ i }) => runOne(i)))
  if (selectedIndex.value === null) {
    const firstDone = files.value.findIndex((f) => f.result)
    if (firstDone !== -1) selectedIndex.value = firstDone
  }
  isRunning.value = false
}

const rerunSelected = () => {
  if (selectedIndex.value !== null) runOne(selectedIndex.value)
}

const openDetail = (result: AnalyzeResponse | null) => {
  if (result?.detection_id) router.push(`/analysis/${result.detection_id}`)
}
</script>

<style scoped>
.batch-row {
  transition: background 0.15s ease;
}

.batch-row:hover {
  background: var(--bg-sunken);
}

.batch-row--active {
  background: var(--accent-bg);
}
</style>
