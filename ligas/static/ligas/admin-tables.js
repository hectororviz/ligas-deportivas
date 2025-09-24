(function(){
  const BOOLEAN_TRUE = new Set(['si', 'true', '1', 'activo', 'activa']);
  const BOOLEAN_FALSE = new Set(['no', 'false', '0', 'inactivo', 'inactiva']);

  function normalizeText(value) {
    let text = (value || '').toString();
    if (text.normalize) {
      text = text
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
    }
    return text.toLowerCase().trim();
  }

  function parseBooleanValue(text) {
    const normalized = normalizeText(text);
    if (BOOLEAN_TRUE.has(normalized)) return 'true';
    if (BOOLEAN_FALSE.has(normalized)) return 'false';
    return normalized;
  }

  function getSortValue(cell, type) {
    if (!cell) return '';
    const dataValue = cell.getAttribute('data-sort-value');
    if (dataValue !== null) return dataValue;
    const raw = cell.textContent || '';
    if (type === 'boolean') {
      return parseBooleanValue(raw) === 'true' ? '1' : '0';
    }
    return normalizeText(raw);
  }

  function initTable(table) {
    if (!table || table.dataset.enhanced === '1') return;
    const thead = table.tHead;
    const tbody = table.tBodies[0];
    if (!thead || !tbody) return;
    const headerRow = thead.rows[0];
    if (!headerRow) return;

    const headers = Array.from(headerRow.cells);
    if (!headers.length) return;

    const filterRow = thead.insertRow(1);
    filterRow.classList.add('table-filters');

    const filterConfigs = [];
    const sortTypes = [];
    let dataRows = Array.from(tbody.rows).filter(row => !row.classList.contains('empty-row'));
    const defaultOrder = dataRows.slice();
    const emptyRow = Array.from(tbody.rows).find(row => row.classList.contains('empty-row'));
    const currentSort = { index: null, dir: null };

    function applyFilters() {
      let visibleCount = 0;
      dataRows.forEach(row => {
        let visible = true;
        for (const cfg of filterConfigs) {
          const cell = row.cells[cfg.index];
          const text = cell ? cell.textContent || '' : '';
          if (cfg.type === 'text') {
            const query = normalizeText(cfg.getValue());
            if (query && normalizeText(text).indexOf(query) === -1) {
              visible = false;
              break;
            }
          } else if (cfg.type === 'boolean') {
            const selected = cfg.getValue();
            if (selected && parseBooleanValue(text) !== selected) {
              visible = false;
              break;
            }
          }
        }
        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount += 1;
      });
      if (emptyRow) {
        emptyRow.style.display = visibleCount ? 'none' : '';
      }
    }

    function setSortIndicators(index, direction) {
      headers.forEach((th, idx) => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.sortable !== 'false' && th.classList.contains('sortable')) {
          const ariaValue = (index === idx && direction)
            ? (direction === 'asc' ? 'ascending' : 'descending')
            : 'none';
          th.setAttribute('aria-sort', ariaValue);
        }
      });
    }

    function applySort(index, direction) {
      let ordered;
      if (!direction) {
        ordered = defaultOrder.slice();
        currentSort.index = null;
        currentSort.dir = null;
      } else {
        const sortType = sortTypes[index] || 'text';
        ordered = defaultOrder.slice().sort((a, b) => {
          const aVal = getSortValue(a.cells[index], sortType);
          const bVal = getSortValue(b.cells[index], sortType);
          if (aVal < bVal) return direction === 'asc' ? -1 : 1;
          if (aVal > bVal) return direction === 'asc' ? 1 : -1;
          return 0;
        });
        currentSort.index = index;
        currentSort.dir = direction;
      }
      dataRows = ordered;
      ordered.forEach(row => tbody.appendChild(row));
      if (emptyRow) {
        tbody.appendChild(emptyRow);
      }
      setSortIndicators(currentSort.index, currentSort.dir);
      applyFilters();
    }

    function toggleSort(index) {
      if (headers[index].dataset.sortable === 'false') return;
      let nextDir = 'asc';
      if (currentSort.index === index) {
        if (currentSort.dir === 'asc') nextDir = 'desc';
        else if (currentSort.dir === 'desc') nextDir = null;
      }
      applySort(index, nextDir);
    }

    headers.forEach((th, index) => {
      const filterType = th.dataset.filter;
      const sortType = th.dataset.sort || (filterType === 'boolean' ? 'boolean' : 'text');
      sortTypes[index] = sortType;

      const filterCell = document.createElement('th');
      filterCell.setAttribute('scope', 'col');
      filterRow.appendChild(filterCell);

      if (filterType === 'text') {
        const input = document.createElement('input');
        input.type = 'search';
        input.placeholder = 'Filtrar…';
        input.setAttribute('aria-label', 'Filtrar ' + (th.textContent || '').trim());
        input.addEventListener('input', applyFilters);
        filterCell.appendChild(input);
        filterConfigs.push({ type: 'text', index, getValue: () => input.value });
      } else if (filterType === 'boolean') {
        const select = document.createElement('select');
        select.innerHTML = '<option value="">Todos</option><option value="true">Sí</option><option value="false">No</option>';
        select.setAttribute('aria-label', 'Filtrar ' + (th.textContent || '').trim());
        select.addEventListener('change', applyFilters);
        filterCell.appendChild(select);
        filterConfigs.push({ type: 'boolean', index, getValue: () => select.value });
      } else {
        filterCell.innerHTML = '';
      }

      if (th.dataset.sortable !== 'false') {
        th.classList.add('sortable');
        if (!th.hasAttribute('tabindex')) {
          th.setAttribute('tabindex', '0');
        }
        if (!th.hasAttribute('aria-sort')) {
          th.setAttribute('aria-sort', 'none');
        }
        const handler = (event) => {
          if (event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') return;
          event.preventDefault();
          toggleSort(index);
        };
        th.addEventListener('click', handler);
        th.addEventListener('keydown', handler);
      }
    });

    table.dataset.enhanced = '1';
    setSortIndicators(currentSort.index, currentSort.dir);
    applyFilters();
  }

  function initAll(root) {
    (root || document).querySelectorAll('table[data-enhanced-list]').forEach(initTable);
  }

  window.AdminTables = {
    init: function(root) {
      initAll(root || document);
    }
  };

  if (document.readyState !== 'loading') {
    initAll(document);
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      initAll(document);
    });
  }
})();
