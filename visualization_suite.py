"""
Comprehensive Visualization Suite for [[5,1,3]] QEC Code Analysis
Generates circuit diagrams, fidelity plots, error correction comparisons, and scaling visualizations
Author: Arijit (Member 3 - Data Scientist)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
from typing import Dict, List, Tuple
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class VisualizationSuite:
    """
    Comprehensive visualization tools for QEC analysis
    """
    
    def __init__(self, output_dir: str = 'Arijit/figures'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Visualization output directory: {output_dir}")
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 11
    
    def plot_error_syndrome_heatmap(self, error_to_syndrome: Dict, 
                                    filename: str = 'error_syndrome_heatmap.png') -> None:
        """
        Visualize error-to-syndrome mapping as heatmap
        
        Args:
            error_to_syndrome: Dictionary mapping errors to syndrome values
            filename: Output filename
        """
        logger.info(f"Generating error-syndrome heatmap: {filename}")
        
        # Extract syndrome values
        syndromes = list(error_to_syndrome.values())
        errors = list(error_to_syndrome.keys())
        
        # Create matrix for heatmap (5 qubits × 3 error types)
        heatmap_data = np.zeros((5, 3))
        error_labels = []
        
        for i, (error, syndrome) in enumerate(error_to_syndrome.items()):
            if error != 'I':
                parts = error.split('_')
                if len(parts) == 2:
                    qubit = int(parts[0].replace('Qubit', ''))
                    error_type = parts[1]
                    error_idx = {'X': 0, 'Z': 1, 'Y': 2}[error_type]
                    heatmap_data[qubit, error_idx] = syndrome
        
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
        
        ax.set_xlabel('Error Type', fontsize=12, fontweight='bold')
        ax.set_ylabel('Qubit Index', fontsize=12, fontweight='bold')
        ax.set_title('Error-to-Syndrome Mapping for [[5,1,3]] Code', 
                    fontsize=14, fontweight='bold')
        
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(['X-Error', 'Z-Error', 'Y-Error'])
        ax.set_yticks(range(5))
        
        # Add text annotations
        for i in range(5):
            for j in range(3):
                text = ax.text(j, i, f'{int(heatmap_data[i, j])}',
                             ha="center", va="center", color="black", fontsize=10)
        
        plt.colorbar(im, ax=ax, label='Syndrome Value')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150, bbox_inches='tight')
        logger.info(f"Saved heatmap to {os.path.join(self.output_dir, filename)}")
        plt.close()
    
    def plot_fidelity_comparison(self, error_scenarios: Dict[str, float],
                                 filename: str = 'fidelity_comparison.png') -> None:
        """
        Compare fidelity across different error scenarios
        
        Args:
            error_scenarios: Dict mapping scenario names to fidelity values
            filename: Output filename
        """
        logger.info(f"Generating fidelity comparison plot: {filename}")
        
        scenarios = list(error_scenarios.keys())
        fidelities = list(error_scenarios.values())
        
        colors = ['#2ecc71' if f > 0.8 else '#f39c12' if f > 0.5 else '#e74c3c' 
                 for f in fidelities]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(scenarios, fidelities, color=colors, edgecolor='black', linewidth=1.5)
        
        # Add value labels on bars
        for bar, fidelity in zip(bars, fidelities):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{fidelity:.3f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_ylabel('Fidelity', fontsize=12, fontweight='bold')
        ax.set_xlabel('Error Scenario', fontsize=12, fontweight='bold')
        ax.set_title('Quantum State Fidelity Across Error Scenarios', 
                    fontsize=14, fontweight='bold')
        ax.set_ylim([0, 1.1])
        ax.axhline(y=0.9, color='green', linestyle='--', linewidth=2, alpha=0.5, label='Acceptable (>0.9)')
        ax.axhline(y=0.5, color='orange', linestyle='--', linewidth=2, alpha=0.5, label='Moderate (>0.5)')
        
        ax.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150, bbox_inches='tight')
        logger.info(f"Saved fidelity comparison to {os.path.join(self.output_dir, filename)}")
        plt.close()
    
    def plot_error_rate_vs_logical_error(self, physical_error_rates: List[float],
                                        logical_error_rates: List[float],
                                        with_qec: bool = True,
                                        filename: str = 'threshold_plot.png') -> None:
        """
        Plot threshold theorem: physical error rate vs logical error rate
        Shows where QEC becomes beneficial
        
        Args:
            physical_error_rates: Array of physical error rates
            logical_error_rates: Array of corresponding logical error rates
            with_qec: Boolean indicating if this includes error correction
            filename: Output filename
        """
        logger.info(f"Generating threshold plot: {filename}")
        
        fig, ax = plt.subplots(figsize=(10, 7))
        
        label = 'With QEC' if with_qec else 'Without QEC'
        color = '#2ecc71' if with_qec else '#e74c3c'
        marker = 'o' if with_qec else 's'
        
        ax.plot(physical_error_rates, logical_error_rates, marker=marker, 
               markersize=8, linewidth=2.5, label=label, color=color)
        
        # Ideal case: logical error = physical error
        ideal_line = np.array(physical_error_rates)
        ax.plot(physical_error_rates, ideal_line, 'k--', linewidth=2, 
               label='No Correction', alpha=0.6)
        
        # Threshold region
        ax.fill_between(physical_error_rates, 0, ideal_line, alpha=0.1, color='red', 
                       label='Threshold Region')
        
        ax.set_xlabel('Physical Error Rate (p)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Logical Error Rate (p_L)', fontsize=12, fontweight='bold')
        ax.set_title('Threshold Theorem: Quantum Error Correction Effectiveness', 
                    fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.grid(True, which='both', alpha=0.3)
        ax.legend(fontsize=11)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150, bbox_inches='tight')
        logger.info(f"Saved threshold plot to {os.path.join(self.output_dir, filename)}")
        plt.close()
    
    def plot_error_distribution(self, error_counts: Dict[str, int],
                               filename: str = 'error_distribution.png') -> None:
        """
        Visualize distribution of error types and locations
        
        Args:
            error_counts: Dict mapping error descriptions to counts
            filename: Output filename
        """
        logger.info(f"Generating error distribution plot: {filename}")
        
        errors = list(error_counts.keys())
        counts = list(error_counts.values())
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(errors)))
        wedges, texts, autotexts = ax.pie(counts, labels=errors, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        ax.set_title('Distribution of Error Types and Locations', 
                    fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150, bbox_inches='tight')
        logger.info(f"Saved error distribution to {os.path.join(self.output_dir, filename)}")
        plt.close()
    
    def plot_measurement_statistics(self, syndrome_measurements: Dict[int, int],
                                   filename: str = 'syndrome_statistics.png') -> None:
        """
        Visualize syndrome measurement statistics
        
        Args:
            syndrome_measurements: Dict mapping syndrome values to measurement counts
            filename: Output filename
        """
        logger.info(f"Generating syndrome statistics plot: {filename}")
        
        syndromes = sorted(syndrome_measurements.keys())
        counts = [syndrome_measurements[s] for s in syndromes]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars = ax.bar(range(len(syndromes)), counts, color='#3498db', edgecolor='black', linewidth=1.5)
        
        # Add value labels
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(count)}',
                   ha='center', va='bottom', fontsize=9)
        
        ax.set_xlabel('Syndrome Value (binary)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Measurement Frequency', fontsize=12, fontweight='bold')
        ax.set_title('Syndrome Measurement Statistics for [[5,1,3]] Code', 
                    fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(syndromes)))
        ax.set_xticklabels([f'{s:04b}' for s in syndromes], rotation=45)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150, bbox_inches='tight')
        logger.info(f"Saved syndrome statistics to {os.path.join(self.output_dir, filename)}")
        plt.close()
    
    def plot_scaling_analysis(self, code_types: List[str],
                             qubit_counts: List[int],
                             error_correcting_capability: List[int],
                             filename: str = 'qec_scaling.png') -> None:
        """
        Plot scaling of quantum error correction codes
        Shows relationship between code parameters and resources
        
        Args:
            code_types: Names of QEC codes
            qubit_counts: Number of physical qubits per code
            error_correcting_capability: t value (max errors correctable)
            filename: Output filename
        """
        logger.info(f"Generating QEC scaling plot: {filename}")
        
        fig = plt.figure(figsize=(14, 8))
        gs = GridSpec(2, 2, figure=fig)
        
        # Plot 1: Qubit overhead
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.bar(code_types, qubit_counts, color='#e74c3c', edgecolor='black', linewidth=1.5)
        ax1.set_ylabel('Physical Qubits', fontsize=11, fontweight='bold')
        ax1.set_title('Physical Qubit Overhead', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # Plot 2: Error correction capability
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.bar(code_types, error_correcting_capability, color='#2ecc71', edgecolor='black', linewidth=1.5)
        ax2.set_ylabel('Error Correcting Capability (t)', fontsize=11, fontweight='bold')
        ax2.set_title('Maximum Correctable Errors', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        # Plot 3: Efficiency ratio
        ax3 = fig.add_subplot(gs[1, 0])
        efficiency = np.array(error_correcting_capability) / np.array(qubit_counts)
        ax3.bar(code_types, efficiency, color='#f39c12', edgecolor='black', linewidth=1.5)
        ax3.set_ylabel('Efficiency (t/n)', fontsize=11, fontweight='bold')
        ax3.set_title('QEC Efficiency: Error Correction per Qubit', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        
        # Plot 4: Code distance and qubit relationship
        ax4 = fig.add_subplot(gs[1, 1])
        code_distances = [2*t + 1 for t in error_correcting_capability]
        ax4.scatter(qubit_counts, code_distances, s=200, color='#9b59b6', edgecolor='black', linewidth=2)
        for i, code in enumerate(code_types):
            ax4.annotate(code, (qubit_counts[i], code_distances[i]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=10)
        ax4.set_xlabel('Physical Qubits (n)', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Code Distance (d = 2t+1)', fontsize=11, fontweight='bold')
        ax4.set_title('Code Distance vs Qubit Count', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle('Quantum Error Correction Code Scaling Analysis', 
                    fontsize=16, fontweight='bold', y=1.00)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150, bbox_inches='tight')
        logger.info(f"Saved scaling analysis to {os.path.join(self.output_dir, filename)}")
        plt.close()
    
    def create_summary_report_figures(self) -> None:
        """
        Create a comprehensive summary figure combining multiple subplots
        """
        logger.info("Creating comprehensive summary report figures")
        
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.35)
        
        # Title
        fig.suptitle('Perfect [[5,1,3]] Quantum Error Correction - Comprehensive Analysis', 
                    fontsize=18, fontweight='bold', y=0.995)
        
        # Placeholder subplots (can be filled with actual data)
        titles = [
            'Error-Syndrome Mapping',
            'Fidelity Comparison',
            'Threshold Theorem',
            'Circuit Depth Analysis',
            'Syndrome Distribution',
            'Error Recovery Rate',
            'Scaling Properties',
            'Resource Comparison',
            'Performance Summary'
        ]
        
        for i, title in enumerate(row := (i // 3, i % 3)):
            ax = fig.add_subplot(gs[row])
            ax.text(0.5, 0.5, title, ha='center', va='center', 
                   transform=ax.transAxes, fontsize=13, fontweight='bold')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
        
        plt.savefig(os.path.join(self.output_dir, 'summary_layout.png'), 
                   dpi=150, bbox_inches='tight')
        logger.info("Created summary layout figure")
        plt.close()
