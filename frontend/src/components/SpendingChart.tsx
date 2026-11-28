import ReactECharts from 'echarts-for-react'

const option = {
  backgroundColor: 'transparent',
  animation: true,
  animationDuration: 1100,
  animationEasing: 'cubicOut',
  grid: {
    top: 18,
    right: 12,
    bottom: 25,
    left: 42,
    containLabel: false,
  },
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#172235',
    borderColor: '#3c5276',
    borderWidth: 1,
    textStyle: { color: '#edf3ff', fontSize: 11 },
    axisPointer: {
      type: 'line',
      lineStyle: { color: '#8eafff', type: 'dashed' },
    },
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: ['01', '03', '05', '07', '09', '11', '13', '15', '17', '19', '21', '23'],
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#75849a', fontSize: 9, margin: 12 },
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 8000,
    interval: 2000,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: '#75849a',
      fontSize: 9,
      formatter: (value: number) => value === 0 ? '₹0' : `₹${value / 1000}k`,
    },
    splitLine: {
      lineStyle: { color: '#293344', type: 'dashed', opacity: 0.7 },
    },
  },
  series: [{
    name: 'Daily spending',
    type: 'line',
    smooth: 0.42,
    symbol: 'circle',
    symbolSize: 7,
    showSymbol: false,
    data: [2400, 3300, 2700, 4600, 3700, 5300, 3200, 4100, 2900, 5900, 3900, 4800],
    lineStyle: {
      width: 3,
      color: '#83a8ff',
      shadowColor: '#648fff88',
      shadowBlur: 12,
    },
    itemStyle: {
      color: '#9dbaff',
      borderColor: '#e1ebff',
      borderWidth: 2,
    },
    emphasis: {
      focus: 'series',
      scale: 1.5,
      itemStyle: { color: '#ffffff', borderColor: '#83a8ff', borderWidth: 3 },
    },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(100,143,255,0.34)' },
          { offset: 0.65, color: 'rgba(75,112,200,0.09)' },
          { offset: 1, color: 'rgba(75,112,200,0.005)' },
        ],
      },
    },
    markPoint: {
      symbol: 'circle',
      symbolSize: 11,
      itemStyle: {
        color: '#b6ceff',
        borderColor: '#426fd4',
        borderWidth: 3,
      },
      data: [{ type: 'max', name: 'Peak spending' }],
    },
  }],
}

export default function SpendingChart() {
  return (
    <div className="echarts-spending">
      <ReactECharts
        option={option}
        notMerge
        lazyUpdate
        style={{ width: '100%', height: '100%' }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}
