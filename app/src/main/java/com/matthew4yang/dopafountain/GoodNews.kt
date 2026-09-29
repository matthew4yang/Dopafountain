package com.matthew4yang.dopafountain

data class GoodNews(val title: String, val text: String)

object GoodNewsPool {
    private val seed = listOf(
        GoodNews("世界又好了一点", "越来越多疾病正在从“只能控制”走向更精准的早期发现和个体化治疗。"),
        GoodNews("科学正在悄悄推进", "材料、电池和能源技术持续提高效率，同样的资源正在做更多的事。"),
        GoodNews("自然有恢复能力", "许多曾经濒危的物种在持续保护后，种群数量已经重新增长。"),
        GoodNews("人类还在探索", "新的望远镜、探测器和航天任务正在不断扩大我们能直接观察的宇宙范围。"),
        GoodNews("今天也有人在解决问题", "世界各地每天都有研究者、工程师、医生和普通人在把一个具体问题变小一点。"),
        GoodNews("好消息不一定很响", "很多生态修复、疾病控制和公共安全改善发生得很慢，所以很少成为头条。")
    )
    fun random(): GoodNews = seed.random()
}
