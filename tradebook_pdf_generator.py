#!/usr/bin/env python3
"""
PDF Tradebook Generator for Strategy Simulation Results

Generates comprehensive PDF reports containing simulation results,
performance analytics, brokerage details, and complete trade history.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, blue, red, green
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from datetime import datetime, timedelta
import io
import base64
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TradebookPDFGenerator:
    """
    Comprehensive PDF tradebook generator for strategy simulation results
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Setup custom styles for the PDF report"""
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1f4e79'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Section heading style
        self.section_style = ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#2c5aa0'),
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        # Subsection style
        self.subsection_style = ParagraphStyle(
            'SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=HexColor('#4472c4'),
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        # Key metric style
        self.metric_style = ParagraphStyle(
            'MetricStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=black,
            spaceBefore=6,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        # Positive performance style
        self.positive_style = ParagraphStyle(
            'PositiveStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#00B050'),
            fontName='Helvetica-Bold'
        )
        
        # Negative performance style
        self.negative_style = ParagraphStyle(
            'NegativeStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#C5504B'),
            fontName='Helvetica-Bold'
        )
        
        # Table header style
        self.table_header_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4472c4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f2f2f2')),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ])
    
    def generate_tradebook(self, simulation_results: Dict[str, Any], strategy_name: str) -> bytes:
        """
        Generate complete PDF tradebook from simulation results
        
        Args:
            simulation_results: Complete simulation results dictionary
            strategy_name: Name of the strategy for the filename
            
        Returns:
            bytes: PDF content as bytes
        """
        logger.info(f"🔄 Generating PDF tradebook for strategy: {strategy_name}")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build PDF content
        story = []
        
        # Add all sections
        story.extend(self._add_title_page(simulation_results, strategy_name))
        story.append(PageBreak())
        
        story.extend(self._add_executive_summary(simulation_results))
        story.append(PageBreak())
        
        story.extend(self._add_simulation_parameters(simulation_results))
        story.append(Spacer(1, 20))
        
        story.extend(self._add_performance_analytics(simulation_results))
        story.append(PageBreak())
        
        story.extend(self._add_performance_chart(simulation_results))
        story.append(Spacer(1, 20))
        
        story.extend(self._add_brokerage_analysis(simulation_results))
        story.append(Spacer(1, 20))
        
        story.extend(self._add_benchmark_comparison(simulation_results))
        story.append(PageBreak())
        
        story.extend(self._add_trade_history(simulation_results))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"✅ PDF tradebook generated successfully ({len(pdf_bytes)} bytes)")
        return pdf_bytes
    
    def _add_title_page(self, results: Dict[str, Any], strategy_name: str) -> List:
        """Add title page with strategy overview"""
        story = []
        
        # Main title
        story.append(Paragraph(f"Strategy Tradebook Report", self.title_style))
        story.append(Spacer(1, 20))
        
        # Strategy name
        story.append(Paragraph(f"<b>Strategy:</b> {strategy_name}", self.section_style))
        story.append(Spacer(1, 30))
        
        # Key metrics summary table
        params = results.get('params', {})
        final_value = results.get('final_portfolio_value', 0)
        initial_capital = params.get('portfolio_base_value', 100000)
        total_return = ((final_value / initial_capital) - 1) * 100 if initial_capital > 0 else 0
        
        # Get summary data if available
        summary = results.get('summary', {})
        benchmark_return = summary.get('benchmark_return', 0)
        alpha = summary.get('alpha', total_return - benchmark_return)
        
        summary_data = [
            ['Metric', 'Value'],
            ['Simulation Period', f"{params.get('start_date', 'N/A')} to {params.get('end_date', 'N/A')}"],
            ['Universe', params.get('universe', 'N/A')],
            ['Benchmark', params.get('benchmark_symbol', 'N/A')],
            ['Initial Capital', f"₹{initial_capital:,.2f}"],
            ['Final Portfolio Value', f"₹{final_value:,.2f}"],
            ['Total Return', f"{total_return:+.2f}%"],
            ['Benchmark Return', f"{benchmark_return:+.2f}%"],
            ['Alpha (Outperformance)', f"{alpha:+.2f}%"],
            ['Max Holdings', str(params.get('max_holdings', 'N/A'))],
            ['Rebalance Frequency', params.get('rebalance_frequency', 'N/A')],
            ['Generated On', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
        summary_table.setStyle(self.table_header_style)
        story.append(summary_table)
        
        return story
    
    def _add_executive_summary(self, results: Dict[str, Any]) -> List:
        """Add executive summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        # Performance overview
        params = results.get('params', {})
        final_value = results.get('final_portfolio_value', 0)
        initial_capital = params.get('portfolio_base_value', 100000)
        total_return = ((final_value / initial_capital) - 1) * 100 if initial_capital > 0 else 0
        
        # Calculate additional metrics
        portfolio_history = results.get('portfolio_history', [])
        if len(portfolio_history) > 1:
            # Calculate max drawdown
            values = [day.get('portfolio_value', 0) for day in portfolio_history]
            peak = values[0]
            max_drawdown = 0
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100
                max_drawdown = max(max_drawdown, drawdown)
        else:
            max_drawdown = 0
        
        # Total trades
        total_trades = len(results.get('trades', []))
        
        # Summary text
        performance_color = 'green' if total_return >= 0 else 'red'
        
        summary_text = f"""
        <b>Strategy Performance Overview:</b><br/><br/>
        
        This strategy simulation was executed over the period from {params.get('start_date', 'N/A')} to {params.get('end_date', 'N/A')} 
        using the {params.get('universe', 'N/A')} stock universe. The strategy employed {params.get('momentum_ranking', 'momentum-based')} 
        stock selection with {params.get('rebalance_frequency', 'periodic')} rebalancing.<br/><br/>
        
        <b>Key Results:</b><br/>
        • <font color="{performance_color}"><b>Total Return: {total_return:+.2f}%</b></font><br/>
        • Maximum Drawdown: {max_drawdown:.2f}%<br/>
        • Total Trades Executed: {total_trades:,}<br/>
        • Final Portfolio Value: ₹{final_value:,.2f}<br/><br/>
        
        The strategy {'outperformed' if total_return > 0 else 'underperformed'} expectations with a 
        {'positive' if total_return >= 0 else 'negative'} return over the simulation period.
        """
        
        story.append(Paragraph(summary_text, self.metric_style))
        
        return story
    
    def _add_simulation_parameters(self, results: Dict[str, Any]) -> List:
        """Add simulation parameters section"""
        story = []
        
        story.append(Paragraph("Simulation Configuration", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        params = results.get('params', {})
        
        # Parameters table
        param_data = [
            ['Parameter', 'Value', 'Description'],
            ['Universe', params.get('universe', 'N/A'), 'Stock universe for selection'],
            ['Start Date', params.get('start_date', 'N/A'), 'Simulation start date'],
            ['End Date', params.get('end_date', 'N/A'), 'Simulation end date'],
            ['Initial Capital', f"₹{params.get('portfolio_base_value', 0):,.2f}", 'Starting portfolio value'],
            ['Max Holdings', str(params.get('max_holdings', 'N/A')), 'Maximum stocks in portfolio'],
            ['Rebalance Frequency', params.get('rebalance_frequency', 'N/A'), 'Portfolio rebalancing frequency'],
            ['Rebalance Type', params.get('rebalance_type', 'N/A'), 'Allocation method used'],
            ['Momentum Method', params.get('momentum_ranking', 'N/A'), 'Stock selection criteria'],
            ['Include Brokerage', str(params.get('include_brokerage', False)), 'Transaction charges included'],
            ['Exchange', params.get('exchange', 'N/A'), 'Primary exchange for trading']
        ]
        
        param_table = Table(param_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
        param_table.setStyle(self.table_header_style)
        story.append(param_table)
        
        return story
    
    def _add_performance_analytics(self, results: Dict[str, Any]) -> List:
        """Add detailed performance analytics"""
        story = []
        
        story.append(Paragraph("Performance Analytics", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        # Get summary data if available, otherwise calculate
        summary = results.get('summary', {})
        params = results.get('params', {})
        
        # Use summary data first, then fallback to calculations
        total_return = summary.get('total_return', 0)
        max_drawdown = summary.get('max_drawdown', 0)
        sharpe_ratio = summary.get('sharpe_ratio', 0)
        total_trades = summary.get('total_trades', 0)
        
        # If no summary data, calculate from portfolio history
        if total_return == 0 or max_drawdown == 0:
            portfolio_history = results.get('portfolio_history', [])
            final_value = results.get('final_portfolio_value', 0)
            initial_capital = params.get('portfolio_base_value', 100000)
            
            if final_value > 0 and initial_capital > 0:
                total_return = ((final_value / initial_capital) - 1) * 100
            
            if len(portfolio_history) > 1:
                # Calculate max drawdown from portfolio history
                values = [day.get('portfolio_value', 0) for day in portfolio_history]
                peak = values[0]
                calculated_max_drawdown = 0
                for value in values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak * 100
                    calculated_max_drawdown = max(calculated_max_drawdown, drawdown)
                
                if max_drawdown == 0:
                    max_drawdown = calculated_max_drawdown
        
        # Calculate additional metrics from trades
        trades = results.get('trades', [])
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0
        
        for trade in trades:
            if trade.get('action') == 'SELL':
                pnl = trade.get('pnl', 0)
                if pnl > 0:
                    winning_trades += 1
                    total_profit += pnl
                elif pnl < 0:
                    losing_trades += 1
                    total_loss += abs(pnl)
        
        total_closed_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # If total_trades is 0 from summary, use length of trades array
        if total_trades == 0:
            total_trades = len(trades)
        
        # Performance metrics table
        perf_data = [
            ['Metric', 'Value', 'Analysis'],
            ['Total Return', f"{total_return:+.2f}%", f"{'Strong' if total_return > 15 else 'Moderate' if total_return > 0 else 'Poor'} performance"],
            ['Maximum Drawdown', f"{max_drawdown:.2f}%", f"{'Low' if max_drawdown < 10 else 'Moderate' if max_drawdown < 20 else 'High'} risk"],
            ['Sharpe Ratio', f"{sharpe_ratio:.2f}", f"{'Excellent' if sharpe_ratio > 2 else 'Good' if sharpe_ratio > 1 else 'Poor'} risk-adjusted return"],
            ['Win Rate', f"{win_rate:.1f}%", f"{'High' if win_rate > 60 else 'Moderate' if win_rate > 40 else 'Low'} success rate"],
            ['Total Trades', f"{total_trades}", "Trade frequency"],
            ['Winning Trades', f"{winning_trades}", f"{winning_trades}/{total_closed_trades} profitable"],
            ['Losing Trades', f"{losing_trades}", f"{losing_trades}/{total_closed_trades} unprofitable"],
            ['Average Win', f"₹{avg_win:,.2f}", "Per winning trade"],
            ['Average Loss', f"₹{avg_loss:,.2f}", "Per losing trade"],
            ['Profit Factor', f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞", 
             f"{'Excellent' if profit_factor > 2 else 'Good' if profit_factor > 1.5 else 'Poor'} profitability"]
        ]
        
        perf_table = Table(perf_data, colWidths=[2.2*inch, 1.8*inch, 2*inch])
        perf_table.setStyle(self.table_header_style)
        story.append(perf_table)
        
        # Add period-wise returns analysis
        story.append(Spacer(1, 20))
        story.append(Paragraph("Period-wise Performance Analysis", self.subsection_style))
        
        # Calculate monthly/quarterly returns if enough data
        portfolio_history = results.get('portfolio_history', [])
        if len(portfolio_history) > 30:  # At least a month of data
            story.extend(self._add_period_analysis(portfolio_history))
        else:
            story.append(Paragraph("Insufficient data for period-wise analysis (requires >30 days).", self.metric_style))
        
        # Risk metrics section
        story.append(Spacer(1, 20))
        story.append(Paragraph("Risk Analytics", self.subsection_style))
        
        risk_data = [
            ['Risk Metric', 'Value', 'Interpretation'],
            ['Maximum Drawdown', f"{max_drawdown:.2f}%", "Largest peak-to-trough decline"],
            ['Volatility', f"{self._calculate_portfolio_volatility(portfolio_history):.2f}%", "Standard deviation of returns"],
            ['Downside Deviation', f"{self._calculate_downside_deviation(portfolio_history):.2f}%", "Volatility of negative returns only"],
            ['Calmar Ratio', f"{self._calculate_calmar_ratio(total_return, max_drawdown):.2f}", "Return per unit of drawdown risk"],
            ['Recovery Factor', f"{self._calculate_recovery_factor(total_return, max_drawdown):.2f}", "Ability to recover from losses"],
        ]
        
        risk_table = Table(risk_data, colWidths=[2.2*inch, 1.3*inch, 2.5*inch])
        risk_table.setStyle(self.table_header_style)
        story.append(risk_table)
        
        return story
    
    def _add_performance_chart(self, results: Dict[str, Any]) -> List:
        """Add performance chart visualization"""
        story = []
        
        story.append(Paragraph("Portfolio Performance vs Benchmark", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        # Get portfolio history data
        portfolio_history = results.get('portfolio_history', [])
        if not portfolio_history or len(portfolio_history) < 2:
            story.append(Paragraph("Insufficient data for performance chart.", self.metric_style))
            return story
        
        # Prepare data for chart
        dates = []
        portfolio_returns = []
        benchmark_returns = []
        
        initial_portfolio = portfolio_history[0].get('portfolio_value', 100000)
        initial_benchmark = portfolio_history[0].get('benchmark_value', initial_portfolio)
        
        for i, day in enumerate(portfolio_history):
            if i % max(1, len(portfolio_history) // 20) == 0:  # Sample every ~20th point to avoid overcrowding
                portfolio_value = day.get('portfolio_value', initial_portfolio)
                benchmark_value = day.get('benchmark_value', initial_benchmark)
                
                portfolio_return = ((portfolio_value / initial_portfolio) - 1) * 100
                benchmark_return = ((benchmark_value / initial_benchmark) - 1) * 100
                
                dates.append(i)
                portfolio_returns.append(portfolio_return)
                benchmark_returns.append(benchmark_return)
        
        if len(dates) < 2:
            story.append(Paragraph("Insufficient data points for performance chart.", self.metric_style))
            return story
        
        # Calculate final returns for comparison
        final_portfolio_return = portfolio_returns[-1] if portfolio_returns else 0
        final_benchmark_return = benchmark_returns[-1] if benchmark_returns else 0
        
        # Create actual line chart using ReportLab
        try:
            drawing = Drawing(500, 300)
            chart = HorizontalLineChart()
            chart.x = 50
            chart.y = 50
            chart.height = 200
            chart.width = 400
            
            # Sample data for readability (max 30 points)
            sample_interval = max(1, len(dates) // 30)
            sampled_dates = dates[::sample_interval]
            sampled_portfolio = portfolio_returns[::sample_interval]
            sampled_benchmark = benchmark_returns[::sample_interval]
            
            # Prepare chart data
            chart.data = [sampled_portfolio, sampled_benchmark]
            chart.categoryAxis.categoryNames = [f"D{d}" for d in sampled_dates[::max(1, len(sampled_dates)//8)]]
            
            # Chart styling
            chart.lines[0].strokeColor = colors.blue
            chart.lines[0].strokeWidth = 2
            chart.lines[1].strokeColor = colors.red
            chart.lines[1].strokeWidth = 2
            
            # Axis configuration
            min_val = min(min(portfolio_returns), min(benchmark_returns))
            max_val = max(max(portfolio_returns), max(benchmark_returns))
            chart.valueAxis.valueMin = min_val * 1.1 if min_val < 0 else min_val * 0.9
            chart.valueAxis.valueMax = max_val * 1.1
            
            drawing.add(chart)
            story.append(drawing)
            story.append(Spacer(1, 15))
            
            # Chart legend
            legend_text = """
            <b>Chart Legend:</b><br/>
            <font color="blue">━━━ Portfolio Performance</font><br/>
            <font color="red">━━━ Nifty 50 Benchmark</font>
            """
            story.append(Paragraph(legend_text, self.metric_style))
            story.append(Spacer(1, 15))
            
        except Exception as e:
            logger.warning(f"Could not create performance chart: {e}")
            # Fallback to text summary
            chart_summary = f"""
            <b>Performance Chart Summary:</b><br/><br/>
            
            Portfolio Performance: {final_portfolio_return:+.2f}%<br/>
            Benchmark Performance: {final_benchmark_return:+.2f}%<br/>
            Outperformance: {final_portfolio_return - final_benchmark_return:+.2f}%<br/><br/>
            
            <i>Note: Visual chart could not be generated. Data tracked over {len(portfolio_history)} periods.</i>
            """
            story.append(Paragraph(chart_summary, self.metric_style))
        
        # Performance comparison table
        volatility_portfolio = self._calculate_volatility(portfolio_returns)
        volatility_benchmark = self._calculate_volatility(benchmark_returns)
        
        performance_data = [
            ['Metric', 'Portfolio', 'Nifty 50', 'Analysis'],
            ['Total Return', f"{final_portfolio_return:+.2f}%", f"{final_benchmark_return:+.2f}%", 
             f"{'✓ Outperformed' if final_portfolio_return > final_benchmark_return else '✗ Underperformed'} by {abs(final_portfolio_return - final_benchmark_return):.2f}%"],
            ['Volatility', f"{volatility_portfolio:.2f}%", f"{volatility_benchmark:.2f}%", 
             f"{'Lower' if volatility_portfolio < volatility_benchmark else 'Higher'} risk profile"],
            ['Best Day', f"{max(portfolio_returns):+.2f}%", f"{max(benchmark_returns):+.2f}%", "Peak single-day performance"],
            ['Worst Day', f"{min(portfolio_returns):+.2f}%", f"{min(benchmark_returns):+.2f}%", "Maximum single-day loss"],
        ]
        
        performance_table = Table(performance_data, colWidths=[1.3*inch, 1.2*inch, 1.2*inch, 2.3*inch])
        performance_table.setStyle(self.table_header_style)
        story.append(performance_table)
        
        return story
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate volatility (standard deviation) of returns"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        return (variance ** 0.5)
    
    def _calculate_portfolio_volatility(self, portfolio_history: List[Dict]) -> float:
        """Calculate portfolio volatility from daily returns"""
        if len(portfolio_history) < 2:
            return 0.0
        
        daily_returns = []
        for i in range(1, len(portfolio_history)):
            prev_val = portfolio_history[i-1].get('portfolio_value', 0)
            curr_val = portfolio_history[i].get('portfolio_value', 0)
            if prev_val > 0:
                daily_return = (curr_val - prev_val) / prev_val * 100
                daily_returns.append(daily_return)
        
        return self._calculate_volatility(daily_returns)
    
    def _calculate_downside_deviation(self, portfolio_history: List[Dict]) -> float:
        """Calculate downside deviation (volatility of negative returns only)"""
        if len(portfolio_history) < 2:
            return 0.0
        
        negative_returns = []
        for i in range(1, len(portfolio_history)):
            prev_val = portfolio_history[i-1].get('portfolio_value', 0)
            curr_val = portfolio_history[i].get('portfolio_value', 0)
            if prev_val > 0:
                daily_return = (curr_val - prev_val) / prev_val * 100
                if daily_return < 0:
                    negative_returns.append(daily_return)
        
        return self._calculate_volatility(negative_returns) if negative_returns else 0.0
    
    def _calculate_calmar_ratio(self, total_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio (return/max drawdown)"""
        if max_drawdown == 0:
            return float('inf')
        return total_return / max_drawdown
    
    def _calculate_recovery_factor(self, total_return: float, max_drawdown: float) -> float:
        """Calculate recovery factor (total return/max drawdown)"""
        if max_drawdown == 0:
            return float('inf')
        return total_return / max_drawdown
    
    def _add_period_analysis(self, portfolio_history: List[Dict]) -> List:
        """Add monthly/quarterly performance breakdown"""
        story = []
        
        # Group by months for monthly returns
        monthly_returns = {}
        quarterly_returns = {}
        yearly_returns = {}
        
        # Simple grouping - every 21 trading days ≈ 1 month
        month_size = 21
        quarter_size = 63  # ~3 months
        year_size = 252   # ~1 year
        
        # Calculate monthly returns
        for i in range(0, len(portfolio_history), month_size):
            month_start = i
            month_end = min(i + month_size - 1, len(portfolio_history) - 1)
            
            start_val = portfolio_history[month_start].get('portfolio_value', 0)
            end_val = portfolio_history[month_end].get('portfolio_value', 0)
            
            if start_val > 0:
                month_return = (end_val - start_val) / start_val * 100
                month_label = f"Month {len(monthly_returns) + 1}"
                monthly_returns[month_label] = month_return
        
        # Only show if we have multiple periods
        if len(monthly_returns) > 1:
            # Monthly returns table
            monthly_data = [['Month', 'Return', 'Performance']]
            for month, ret in list(monthly_returns.items())[:12]:  # Show max 12 months
                performance = "Positive" if ret > 0 else "Negative"
                monthly_data.append([month, f"{ret:+.2f}%", performance])
            
            monthly_table = Table(monthly_data, colWidths=[1.5*inch, 1.2*inch, 1.3*inch])
            monthly_table.setStyle(self.table_header_style)
            story.append(monthly_table)
            story.append(Spacer(1, 15))
        
        # Summary statistics
        if monthly_returns:
            avg_monthly = sum(monthly_returns.values()) / len(monthly_returns)
            best_month = max(monthly_returns.values())
            worst_month = min(monthly_returns.values())
            positive_months = sum(1 for ret in monthly_returns.values() if ret > 0)
            
            summary_text = f"""
            <b>Period Summary:</b><br/>
            • Average Monthly Return: {avg_monthly:+.2f}%<br/>
            • Best Month: {best_month:+.2f}%<br/>
            • Worst Month: {worst_month:+.2f}%<br/>
            • Positive Months: {positive_months}/{len(monthly_returns)} ({positive_months/len(monthly_returns)*100:.1f}%)<br/>
            """
            story.append(Paragraph(summary_text, self.metric_style))
        
        return story
    
    def _add_brokerage_analysis(self, results: Dict[str, Any]) -> List:
        """Add brokerage and cost analysis"""
        story = []
        
        story.append(Paragraph("Brokerage & Cost Analysis", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        # Brokerage details
        params = results.get('params', {})
        include_brokerage = params.get('include_brokerage', False)
        
        if include_brokerage:
            total_charges = results.get('cumulative_charges', 0)
            charge_impact = results.get('charge_impact_percent', 0)
            initial_capital = params.get('portfolio_base_value', 100000)
            
            # Brokerage breakdown (if available)
            charge_data = [
                ['Charge Type', 'Rate', 'Description'],
                ['Securities Transaction Tax (STT)', '0.1%', 'On buy & sell transactions'],
                ['NSE Transaction Charges', '0.00297%', 'NSE exchange charges'],
                ['SEBI Charges', '₹10/crore', 'Regulatory charges'],
                ['Stamp Duty', '0.015%', 'On buy transactions only'],
                ['GST', '18%', 'On brokerage + SEBI + transaction charges'],
                ['', '', ''],
                ['Total Charges Incurred', f"₹{total_charges:,.2f}", f"{charge_impact:.3f}% of portfolio"],
                ['Net Impact on Returns', f"{charge_impact:.2f}%", 'Reduction in total returns']
            ]
            
            brokerage_table = Table(charge_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            brokerage_table.setStyle(self.table_header_style)
            story.append(brokerage_table)
            
            # Cost analysis text
            cost_text = f"""
            <b>Cost Impact Analysis:</b><br/><br/>
            The simulation included realistic Indian equity delivery charges, resulting in total 
            transaction costs of ₹{total_charges:,.2f}, which represents {charge_impact:.3f}% of the 
            initial portfolio value. This cost structure reflects actual market conditions and 
            provides realistic performance expectations.<br/><br/>
            
            The net impact on returns is {charge_impact:.2f}%, demonstrating the importance of 
            considering transaction costs in strategy evaluation.
            """
            
            story.append(Spacer(1, 15))
            story.append(Paragraph(cost_text, self.metric_style))
            
        else:
            no_brokerage_text = """
            <b>No Brokerage Charges Applied</b><br/><br/>
            This simulation was run without including transaction costs. For realistic performance 
            evaluation, consider re-running the simulation with brokerage charges enabled to 
            understand the true impact of trading costs on strategy returns.
            """
            story.append(Paragraph(no_brokerage_text, self.metric_style))
        
        return story
    
    def _add_benchmark_comparison(self, results: Dict[str, Any]) -> List:
        """Add benchmark comparison section"""
        story = []
        
        params = results.get('params', {})
        benchmark_name = params.get('benchmark_symbol', 'NIFTY 50')
        
        story.append(Paragraph(f"Benchmark Comparison vs {benchmark_name}", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        # Get actual performance data
        final_value = results.get('final_portfolio_value', 0)
        initial_capital = params.get('portfolio_base_value', 100000)
        strategy_return = ((final_value / initial_capital) - 1) * 100 if initial_capital > 0 else 0
        
        # Debug logging
        logger.info(f"🔍 PDF Debug - Strategy return calculated: {strategy_return:.2f}%")
        
        # Get benchmark data from summary or calculate from portfolio history
        summary = results.get('summary', {})
        benchmark_return = summary.get('benchmark_return', 0)
        
        logger.info(f"🔍 PDF Debug - Summary benchmark return: {benchmark_return}")
        
        # If no summary data, try to calculate from portfolio history
        if benchmark_return == 0:
            portfolio_history = results.get('portfolio_history', [])
            logger.info(f"🔍 PDF Debug - Portfolio history length: {len(portfolio_history)}")
            
            if portfolio_history and len(portfolio_history) > 1:
                initial_benchmark = portfolio_history[0].get('benchmark_value', initial_capital)
                final_benchmark = portfolio_history[-1].get('benchmark_value', initial_capital)
                logger.info(f"🔍 PDF Debug - Benchmark values: initial={initial_benchmark}, final={final_benchmark}")
                
                if initial_benchmark > 0:
                    benchmark_return = ((final_benchmark / initial_benchmark) - 1) * 100
                    logger.info(f"🔍 PDF Debug - Calculated benchmark return: {benchmark_return:.2f}%")
        
        outperformance = strategy_return - benchmark_return
        logger.info(f"🔍 PDF Debug - Final outperformance: {outperformance:.2f}%")
        
        # Additional debug for table data
        strategy_return_str = f"{strategy_return:+.2f}%"
        benchmark_return_str = f"{benchmark_return:+.2f}%"
        outperformance_str = f"{outperformance:+.2f}%"
        
        logger.info(f"🔍 PDF Debug - Table strings: strategy={strategy_return_str}, benchmark={benchmark_return_str}, outperformance={outperformance_str}")
        
        comparison_data = [
            ['Metric', 'Strategy', benchmark_name, 'Difference'],
            ['Total Return', strategy_return_str, benchmark_return_str, outperformance_str],
            ['Risk Metrics', 'Strategy Analysis', 'Benchmark Analysis', 'Comparison'],
            ['Volatility', 'Calculated from returns', 'Market volatility', 'Risk-adjusted performance'],
            ['Max Drawdown', 'Strategy specific', 'Index drawdown', 'Downside protection'],
        ]
        
        comparison_table = Table(comparison_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        comparison_table.setStyle(self.table_header_style)
        story.append(comparison_table)
        
        # Analysis text
        performance_text = f"""
        <b>Benchmark Analysis:</b><br/><br/>
        
        The strategy {'outperformed' if outperformance > 0 else 'underperformed'} the {benchmark_name} 
        benchmark by {abs(outperformance):.2f} percentage points over the simulation period. 
        This {'positive' if outperformance > 0 else 'negative'} alpha suggests that the momentum-based 
        selection strategy {'added' if outperformance > 0 else 'detracted'} value compared to 
        passive index investment.<br/><br/>
        
        <b>Note:</b> Benchmark comparison uses {'actual benchmark data' if benchmark_return != 0 else 'estimated benchmark performance'}. For precise analysis, 
        actual benchmark data for the exact simulation period should be used.
        """
        
        story.append(Spacer(1, 15))
        story.append(Paragraph(performance_text, self.metric_style))
        
        return story
    
    def _add_trade_history(self, results: Dict[str, Any]) -> List:
        """Add complete trade history section"""
        story = []
        
        story.append(Paragraph("Complete Trade History", self.section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#4472c4')))
        story.append(Spacer(1, 15))
        
        trades = results.get('trades', [])
        
        if not trades:
            story.append(Paragraph("No trade data available for this simulation.", self.metric_style))
            return story
        
        # Trade summary
        total_trades = len(trades)
        buy_trades = len([t for t in trades if t.get('action') == 'BUY'])
        sell_trades = len([t for t in trades if t.get('action') == 'SELL'])
        
        summary_text = f"""
        <b>Trade Summary:</b> {total_trades} total trades ({buy_trades} buys, {sell_trades} sells)<br/>
        """
        story.append(Paragraph(summary_text, self.metric_style))
        story.append(Spacer(1, 10))
        
        # Prepare trade data for table
        trade_data = [['Date', 'Symbol', 'Action', 'Quantity', 'Price', 'Value', 'P&L']]
        
        for trade in trades[:50]:  # Limit to first 50 trades to avoid page overflow
            date = trade.get('date', 'N/A')
            symbol = trade.get('symbol', 'N/A')
            action = trade.get('action', 'N/A')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            value = trade.get('value', 0)
            pnl = trade.get('pnl', 0)
            
            # Format P&L with color coding would be nice but complex in reportlab
            pnl_text = f"₹{pnl:,.2f}" if pnl != 0 else "-"
            
            trade_data.append([
                date,
                symbol,
                action,
                f"{quantity:.0f}",
                f"₹{price:.2f}",
                f"₹{value:,.2f}",
                pnl_text
            ])
        
        # Create trade table
        trade_table = Table(trade_data, colWidths=[1*inch, 1*inch, 0.7*inch, 0.8*inch, 1*inch, 1.2*inch, 1*inch])
        
        # Custom style for trade table
        trade_table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4472c4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')])
        ])
        
        trade_table.setStyle(trade_table_style)
        story.append(trade_table)
        
        # Add note if trades were truncated
        if len(trades) > 50:
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<i>Note: Showing first 50 trades of {len(trades)} total trades. Complete trade data available in digital format.</i>", self.metric_style))
        
        return story


def generate_tradebook_pdf(simulation_results: Dict[str, Any], strategy_name: str) -> bytes:
    """
    Main function to generate PDF tradebook
    
    Args:
        simulation_results: Complete simulation results
        strategy_name: Name of the strategy
        
    Returns:
        bytes: PDF content
    """
    try:
        generator = TradebookPDFGenerator()
        pdf_bytes = generator.generate_tradebook(simulation_results, strategy_name)
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"❌ Error generating PDF tradebook: {e}")
        raise
