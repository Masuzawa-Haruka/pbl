(() => {
  const init = () => {
    // 1. 文字数カウンターの連動
    const textarea = document.getElementById('id_description');
    const charCountSpan = document.querySelector('.char-count');

    if (textarea && charCountSpan) {
      const updateCharCount = () => {
        charCountSpan.textContent = `${textarea.value.length}/200`;
      };

      textarea.addEventListener('input', updateCharCount);
      updateCharCount();
    }

    // 1.5. 状態説明文の動的切り替え & カスタムドロップダウン制御
    const conditionSelect = document.getElementById('id_condition');
    const conditionDesc = document.getElementById('id_condition_desc');
    const customSelect = document.getElementById('custom_condition_select');
    const conditionTitle = document.getElementById('id_condition_title');
    
    if (conditionSelect && conditionDesc && customSelect && conditionTitle) {
      const conditionDescriptions = {
        good: '新品で購入・使用していない',
        normal: '数回使用、折り目や書き込みなし',
        used: '使用感はあるが、全体的に綺麗な状態',
        writing: 'マーカーや鉛筆での書き込みがある',
        stain: 'カバーの傷み、ページにシミや折れなどがある',
        bad: '破れや大きな汚れがある'
      };
      
      const updateConditionDesc = () => {
        const val = conditionSelect.value;
        conditionDesc.textContent = conditionDescriptions[val] || '';
      };
      
      conditionSelect.addEventListener('change', updateConditionDesc);
      updateConditionDesc();

      // カスタムドロップダウンの制御
      const trigger = customSelect.querySelector('.custom-select-trigger');
      const options = customSelect.querySelectorAll('.custom-select-option');

      // トグル動作
      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        customSelect.classList.toggle('is-open');
      });

      // 各オプション選択時
      options.forEach(opt => {
        opt.addEventListener('click', (e) => {
          e.stopPropagation();
          const val = opt.getAttribute('data-value');
          const title = opt.querySelector('.option-title').textContent;

          // 本物のselectを更新してイベント発火
          conditionSelect.value = val;
          conditionTitle.textContent = title;
          conditionSelect.dispatchEvent(new Event('change'));

          // 選択クラスの更新
          options.forEach(o => o.classList.remove('is-selected'));
          opt.classList.add('is-selected');

          // 閉じる
          customSelect.classList.remove('is-open');
        });
      });

      // 初期状態で selected なオプションに is-selected を付与する
      const initialVal = conditionSelect.value;
      const initialOpt = customSelect.querySelector(`.custom-select-option[data-value="${initialVal}"]`);
      if (initialOpt) {
        initialOpt.classList.add('is-selected');
      }

      // アウトサイドクリックで閉じる
      document.addEventListener('click', () => {
        customSelect.classList.remove('is-open');
      });
    }

    // 2. 写真の追加・削除機能
    const uploadGrid = document.querySelector('.photo-upload-grid');
    const addBtn = document.querySelector('.photo-add-button');
    const photoInput = document.getElementById('id_photo_input');

    if (uploadGrid && addBtn && photoInput) {
      const checkLimit = () => {
        const thumbs = uploadGrid.querySelectorAll('.photo-thumbnail');
        if (thumbs.length >= 5) {
          addBtn.style.display = 'none';
        } else {
          addBtn.style.display = 'grid';
        }
      };

      const setDeleteEvent = (thumbnailEl, objectUrl = null) => {
        const deleteBtn = thumbnailEl.querySelector('.photo-thumbnail__delete');
        if (deleteBtn) {
          deleteBtn.addEventListener('click', () => {
            thumbnailEl.remove();
            if (objectUrl) {
              URL.revokeObjectURL(objectUrl);
            }
            checkLimit();
          });
        }
      };

      // 初期サムネイルの削除イベント設定
      const initialThumbs = uploadGrid.querySelectorAll('.photo-thumbnail');
      initialThumbs.forEach(thumb => {
        setDeleteEvent(thumb);
      });

      // ＋ボタンクリックでファイル選択ダイアログを開く
      addBtn.addEventListener('click', () => {
        photoInput.click();
      });

      // ファイルが選択されたときの処理
      photoInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        const currentThumbs = uploadGrid.querySelectorAll('.photo-thumbnail');
        const availableSlots = 5 - currentThumbs.length;
        const filesToAdd = files.slice(0, availableSlots);

        filesToAdd.forEach(file => {
          const fileUrl = URL.createObjectURL(file);

          const newThumb = document.createElement('div');
          newThumb.className = 'photo-thumbnail';

          const imgDiv = document.createElement('div');
          imgDiv.className = 'photo-thumbnail__image';

          const imgEl = document.createElement('img');
          imgEl.src = fileUrl;
          imgEl.alt = file.name;
          imgEl.style.width = '100%';
          imgEl.style.height = '100%';
          imgEl.style.objectFit = 'cover';
          imgDiv.appendChild(imgEl);

          const delBtn = document.createElement('button');
          delBtn.type = 'button';
          delBtn.className = 'photo-thumbnail__delete';
          delBtn.setAttribute('aria-label', '写真を削除');
          delBtn.innerHTML = `
            <svg width="8" height="8" viewBox="0 0 8 8" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M1 1L7 7M7 1L1 7" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          `;

          newThumb.appendChild(imgDiv);
          newThumb.appendChild(delBtn);

          uploadGrid.insertBefore(newThumb, addBtn);
          setDeleteEvent(newThumb, fileUrl);
        });

        // 制限チェック
        checkLimit();

        // 選択値をクリアして、同じファイルの再選択でもchangeイベントが動くようにする
        photoInput.value = '';
      });
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
